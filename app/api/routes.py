"""HTTP API routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.account.account_service import AccountService
from app.bot.paper_trading_bot import PaperTradingBot, PaperTradingBotError
from app.backtesting.backtest_engine import BacktestDataError, BacktestEngine
from app.config import get_settings
from app.data.market_data_service import MarketDataService
from app.execution.dry_run_executor import DryRunExecutor
from app.execution.emergency_controls import EmergencyControls
from app.execution.execution_guard import ExecutionGuard
from app.execution.order_intent import OrderIntent
from app.execution.order_validator import OrderValidator
from app.execution.paper_broker import PaperBroker
from app.execution.trade_executor import TradeExecutor
from app.exchanges.kraken_adapter import EmptyMarketDataError, InvalidSymbolError, KrakenRequestError, UnsupportedTimeframeError
from app.risk.risk_manager import RiskManager
from app.reporting.dashboard_service import DashboardService
from app.storage.database import init_db
from app.storage.trade_journal import TradeJournal
from app.strategies.crypto_hunter_strategy import CryptoHunterStrategy
from app.strategies.indicator_engine import IndicatorEngineError
from app.strategies.signal_scoring import SignalScoringError

import pandas as pd

router = APIRouter()
_paper_broker = PaperBroker()
_trade_executor = TradeExecutor(paper_broker=_paper_broker)
_risk_manager = RiskManager()
_paper_bot = PaperTradingBot(risk_manager=_risk_manager, trade_executor=_trade_executor)
_journal = TradeJournal()
_dashboard_service = DashboardService(bot_state=_paper_bot.state, paper_broker=_paper_broker, risk_manager=_risk_manager, trade_journal=_journal)
_account_service = AccountService(journal=_journal)
_order_validator = OrderValidator()
_dry_run_executor = DryRunExecutor(journal=_journal)
_execution_guard = ExecutionGuard()
_emergency_controls = EmergencyControls(bot_state=_paper_bot.state, paper_broker=_paper_broker)


class PaperOrderRequest(BaseModel):
    """Request body for manual paper market orders."""

    symbol: str
    side: str
    quantity: float = Field(gt=0)
    market_price: float = Field(gt=0)
    reason: str | None = None


class PaperCloseRequest(BaseModel):
    """Request body for manual paper position close."""

    market_price: float = Field(gt=0)
    reason: str | None = None


class RiskEvaluateRequest(BaseModel):
    """Request body for risk-only trade evaluation."""

    symbol: str
    side: str
    market_price: float = Field(gt=0)
    spread_bps: float | None = None
    requested_quantity: float | None = None
    signal_result: dict
    account_summary: dict | None = None
    open_positions: list[dict] | dict | None = None
    manual_override: bool = False


class KillSwitchRequest(BaseModel):
    """Request body for kill switch changes."""

    reason: str | None = None


class BotStartRequest(BaseModel):
    """Request body for bot start."""

    manual_start: bool = False


class BacktestSingleRequest(BaseModel):
    """Request body for single-symbol JSON-candle backtest."""

    symbol: str
    timeframe: str = "1h"
    candles: list[dict] = Field(default_factory=list, max_length=5000)


class BacktestWatchlistRequest(BaseModel):
    """Request body for multi-symbol JSON-candle backtest."""

    timeframe: str = "1h"
    symbol_to_candles: dict[str, list[dict]]


class ExecutionOrderRequest(BaseModel):
    """Request body for order-intent validation and dry-run previews."""

    symbol: str
    side: str
    order_type: str = "market"
    quantity: float
    estimated_price: float
    reason: str | None = None
    signal_score: int = 0
    signal_category: str = ""
    risk_approved: bool = False
    risk_decision_id: str | None = None
    risk_decision: dict | None = None
    account_summary: dict | None = None
    ticker: dict | None = None
    asset_pair_constraints: dict | None = None


class EmergencyRequest(BaseModel):
    """Request body for execution emergency controls."""

    reason: str = "manual emergency control"


@router.get("/health")
def health() -> dict:
    """Return service health."""
    return {"status": "ok"}


@router.get("/status")
def status() -> dict:
    """Return safe runtime status without secrets."""
    settings = get_settings()
    return {
        "bot_mode": settings.bot_mode.value,
        "exchange": settings.exchange.value,
        "base_currency": settings.base_currency,
        "allowed_symbols": settings.allowed_symbols,
        "live_trading_enabled": settings.enable_live_trading,
        "live_trading_allowed": settings.live_trading_allowed(),
        "max_open_positions": settings.max_open_positions,
    }


@router.get("/market/symbols")
def market_symbols() -> dict:
    """Return public market symbols from the selected exchange."""
    try:
        return {"symbols": MarketDataService().get_symbols()}
    except KrakenRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/market/ticker/{symbol}")
def market_ticker(symbol: str) -> dict:
    """Return ticker data for a FastAPI-safe symbol such as BTC-USD."""
    try:
        return MarketDataService().get_symbol_ticker(symbol)
    except InvalidSymbolError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmptyMarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except KrakenRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/market/candles/{symbol}")
def market_candles(symbol: str, timeframe: str = Query(default="1h"), limit: int = Query(default=200, ge=1, le=720)) -> dict:
    """Return candles for a FastAPI-safe symbol such as BTC-USD."""
    try:
        return {"candles": MarketDataService().get_symbol_candles(symbol, timeframe=timeframe, limit=limit)}
    except InvalidSymbolError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedTimeframeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmptyMarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except KrakenRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _build_signal_for_symbol(symbol: str, timeframe: str, limit: int) -> dict:
    """Build a signal for one FastAPI-safe symbol."""
    try:
        service = MarketDataService()
        candles = pd.DataFrame(service.get_symbol_candles(symbol, timeframe=timeframe, limit=limit))
        normalized_symbol = symbol.strip().upper().replace("-", "/")
        return CryptoHunterStrategy().evaluate(candles, symbol=normalized_symbol, timeframe=timeframe).to_dict()
    except InvalidSymbolError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedTimeframeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (EmptyMarketDataError, KrakenRequestError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (IndicatorEngineError, SignalScoringError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/signals/watchlist")
def signals_for_watchlist(timeframe: str = Query(default="1h"), limit: int = Query(default=250, ge=200, le=720)) -> dict:
    """Return signals for the configured watchlist using public data only."""
    settings = get_settings()
    results = []
    for symbol in settings.allowed_symbols:
        try:
            results.append(_build_signal_for_symbol(symbol.replace("/", "-"), timeframe=timeframe, limit=limit))
        except HTTPException as exc:
            results.append({"symbol": symbol, "error": exc.detail})
    return {"signals": results}


@router.get("/signals/{symbol}")
def signal_for_symbol(symbol: str, timeframe: str = Query(default="1h"), limit: int = Query(default=250, ge=200, le=720)) -> dict:
    """Return a signal generated from public market data only."""
    return _build_signal_for_symbol(symbol, timeframe=timeframe, limit=limit)


@router.get("/paper/account")
def paper_account() -> dict:
    """Return the in-memory paper account summary."""
    return _paper_broker.get_account_summary()


@router.get("/paper/positions")
def paper_positions() -> dict:
    """Return open paper positions."""
    return {"positions": _paper_broker.get_positions()}


@router.get("/paper/orders")
def paper_orders() -> dict:
    """Return paper orders."""
    return {"orders": _paper_broker.get_orders()}


@router.get("/paper/fills")
def paper_fills() -> dict:
    """Return paper fills."""
    return {"fills": _paper_broker.get_fills()}


@router.post("/paper/order")
def paper_order(request: PaperOrderRequest) -> dict:
    """Simulate a paper market order only."""
    return _trade_executor.execute_paper_market_order(
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        market_price=request.market_price,
        reason=request.reason,
    )


@router.post("/paper/close/{symbol}")
def paper_close(symbol: str, request: PaperCloseRequest) -> dict:
    """Close a paper position using an explicit market price."""
    return _trade_executor.close_paper_position(symbol, market_price=request.market_price, reason=request.reason)


@router.post("/paper/reset")
def paper_reset() -> dict:
    """Reset the in-memory paper account."""
    return _paper_broker.reset()


@router.get("/risk/status")
def risk_status() -> dict:
    """Return risk manager status."""
    return {
        "kill_switch": _risk_manager.kill_switch.status(),
        "settings": {
            "max_risk_per_trade": _risk_manager.settings.max_risk_per_trade,
            "max_daily_loss": _risk_manager.settings.max_daily_loss,
            "max_open_positions": _risk_manager.settings.max_open_positions,
            "max_position_allocation": _risk_manager.settings.max_position_allocation,
            "min_signal_score_to_trade": _risk_manager.settings.min_signal_score_to_trade,
            "max_spread_bps": _risk_manager.settings.max_spread_bps,
        },
    }


@router.post("/risk/evaluate")
def risk_evaluate(request: RiskEvaluateRequest) -> dict:
    """Evaluate risk only; do not execute trades."""
    account_summary = request.account_summary or _paper_broker.get_account_summary()
    open_positions = request.open_positions if request.open_positions is not None else _paper_broker.get_positions()
    decision = _risk_manager.evaluate_trade(
        symbol=request.symbol,
        side=request.side,
        signal_result=request.signal_result,
        account_summary=account_summary,
        open_positions=open_positions,
        market_price=request.market_price,
        spread_bps=request.spread_bps,
        requested_quantity=request.requested_quantity,
        manual_override=request.manual_override,
    )
    return decision.to_dict()


@router.post("/risk/kill-switch/activate")
def risk_kill_switch_activate(request: KillSwitchRequest) -> dict:
    """Activate the risk kill switch."""
    _risk_manager.kill_switch.activate(request.reason or "manual activation")
    return _risk_manager.kill_switch.status()


@router.post("/risk/kill-switch/deactivate")
def risk_kill_switch_deactivate(request: KillSwitchRequest) -> dict:
    """Deactivate the risk kill switch."""
    _risk_manager.kill_switch.deactivate(request.reason)
    return _risk_manager.kill_switch.status()


@router.get("/bot/status")
def bot_status() -> dict:
    """Return paper bot status."""
    return _paper_bot.status()


@router.post("/bot/start")
def bot_start(request: BotStartRequest) -> dict:
    """Start the paper bot without launching a blocking loop."""
    try:
        return _paper_bot.start(manual_start=request.manual_start)
    except PaperTradingBotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bot/stop")
def bot_stop() -> dict:
    """Stop the paper bot."""
    return _paper_bot.stop()


@router.post("/bot/pause")
def bot_pause() -> dict:
    """Pause the paper bot."""
    return _paper_bot.pause()


@router.post("/bot/resume")
def bot_resume() -> dict:
    """Resume the paper bot."""
    return _paper_bot.resume()


@router.post("/bot/scan-once")
def bot_scan_once() -> dict:
    """Run one manual paper scan."""
    try:
        return _paper_bot.scan_once()
    except PaperTradingBotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/journal/init")
def journal_init() -> dict:
    """Initialize journal database tables."""
    init_db()
    return {"status": "ok"}


@router.get("/journal/events")
def journal_events(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return recent bot events."""
    return {"events": _journal.get_recent_bot_events(limit=limit)}


@router.get("/journal/signals")
def journal_signals(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent signal records."""
    return {"signals": _journal.get_recent_signals(limit=limit, symbol=symbol)}


@router.get("/journal/risk-decisions")
def journal_risk_decisions(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent risk decision records."""
    return {"risk_decisions": _journal.get_recent_risk_decisions(limit=limit, symbol=symbol)}


@router.get("/journal/orders")
def journal_orders(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent paper orders."""
    return {"orders": _journal.get_recent_orders(limit=limit, symbol=symbol)}


@router.get("/journal/fills")
def journal_fills(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent paper fills."""
    return {"fills": _journal.get_recent_fills(limit=limit, symbol=symbol)}


@router.get("/journal/positions")
def journal_positions(symbol: str | None = None) -> dict:
    """Return recent paper position snapshots."""
    return {"positions": _journal.get_recent_positions(symbol=symbol)}


@router.get("/journal/account-snapshots")
def journal_account_snapshots(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return recent account snapshots."""
    return {"account_snapshots": _journal.get_recent_account_snapshots(limit=limit)}


@router.get("/journal/scans")
def journal_scans(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent scan results."""
    return {"scan_results": _journal.get_recent_scan_results(limit=limit, symbol=symbol)}


@router.get("/journal/errors")
def journal_errors(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return recent error records."""
    return {"errors": _journal.get_recent_errors(limit=limit)}


@router.post("/backtest/single")
def backtest_single(request: BacktestSingleRequest) -> dict:
    """Run a single-symbol backtest from JSON candles."""
    try:
        result = BacktestEngine().run_single_symbol_backtest(pd.DataFrame(request.candles), request.symbol, request.timeframe)
        return result.to_dict()
    except BacktestDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/backtest/watchlist")
def backtest_watchlist(request: BacktestWatchlistRequest) -> dict:
    """Run watchlist backtests from JSON candles."""
    try:
        frames = {symbol: pd.DataFrame(candles) for symbol, candles in request.symbol_to_candles.items()}
        results = BacktestEngine().run_watchlist_backtest(frames, timeframe=request.timeframe)
        return {"results": {symbol: result.to_dict() for symbol, result in results.items()}}
    except BacktestDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reports/overview")
def report_overview() -> dict:
    """Return read-only dashboard overview."""
    return _dashboard_service.get_overview().to_dict()


@router.get("/reports/paper-performance")
def report_paper_performance() -> dict:
    """Return read-only paper performance."""
    return _dashboard_service.get_paper_performance().to_dict()


@router.get("/reports/signal-performance")
def report_signal_performance(limit: int = Query(default=100, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return read-only signal performance."""
    report = _dashboard_service.get_signal_performance(limit=limit).to_dict()
    if symbol:
        normalized = symbol.upper().replace("-", "/")
        report["recent_signals"] = [signal for signal in report["recent_signals"] if signal.get("symbol") == normalized]
        report["symbols_ranked_by_latest_score"] = [row for row in report["symbols_ranked_by_latest_score"] if row.get("symbol") == normalized]
    return report


@router.get("/reports/risk-summary")
def report_risk_summary() -> dict:
    """Return read-only risk summary."""
    return _dashboard_service.get_risk_summary().to_dict()


@router.get("/reports/recent-activity")
def report_recent_activity(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return read-only recent activity."""
    return _dashboard_service.get_recent_activity(limit=limit).to_dict()


@router.get("/reports/equity-curve")
def report_equity_curve(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return read-only equity curve."""
    return _dashboard_service.get_equity_curve(limit=limit).to_dict()


@router.get("/reports/full-dashboard")
def report_full_dashboard() -> dict:
    """Return full read-only dashboard snapshot."""
    return _dashboard_service.get_full_dashboard_snapshot()


@router.get("/account/status")
def account_status() -> dict:
    """Return read-only Kraken private account connectivity status."""
    return _account_service.get_status()


@router.get("/account/balances")
def account_balances() -> dict:
    """Return read-only Kraken balances or safe disabled response."""
    summary = _account_service.get_account_summary()
    return {
        "exchange": summary.exchange,
        "private_read_enabled": summary.private_read_enabled,
        "configured": summary.configured,
        "balances": [balance.to_dict() for balance in summary.balances],
        "warnings": summary.warnings,
        "source": summary.source,
        "updated_at": summary.updated_at.isoformat(),
    }


@router.get("/account/summary")
def account_summary() -> dict:
    """Return read-only Kraken account summary."""
    return _account_service.get_account_summary().to_dict()


def _build_order_intent(request: ExecutionOrderRequest) -> OrderIntent:
    """Build an order intent from an API request."""
    return OrderIntent(
        symbol=request.symbol,
        side=request.side,
        order_type=request.order_type,
        quantity=request.quantity,
        estimated_price=request.estimated_price,
        reason=request.reason or "Phase 12 validation test",
        signal_score=request.signal_score,
        signal_category=request.signal_category,
        risk_approved=request.risk_approved,
        risk_decision_id=request.risk_decision_id,
    )


@router.get("/execution/safety-status")
def execution_safety_status() -> dict:
    """Return execution safety gate status."""
    return _execution_guard.get_execution_safety_status()


@router.post("/execution/validate-order")
def execution_validate_order(request: ExecutionOrderRequest) -> dict:
    """Validate an order intent without placing an order."""
    intent = _build_order_intent(request)
    result = _order_validator.validate_order_intent(
        intent,
        request.risk_decision,
        account_summary=request.account_summary,
        ticker=request.ticker,
        asset_pair_constraints=request.asset_pair_constraints,
    )
    return result.to_dict()


@router.post("/execution/dry-run-order")
def execution_dry_run_order(request: ExecutionOrderRequest) -> dict:
    """Validate and preview a dry-run order without live execution."""
    intent = _build_order_intent(request)
    validation = _order_validator.validate_order_intent(
        intent,
        request.risk_decision,
        account_summary=request.account_summary,
        ticker=request.ticker,
        asset_pair_constraints=request.asset_pair_constraints,
    )
    return _dry_run_executor.execute_dry_run(intent, validation)


@router.get("/execution/dry-runs")
def execution_dry_runs(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return recent dry-run order previews."""
    return {"dry_runs": _dry_run_executor.get_recent_dry_runs(limit=limit)}


@router.post("/execution/emergency-pause")
def execution_emergency_pause(request: EmergencyRequest) -> dict:
    """Pause the paper bot through emergency controls."""
    return _emergency_controls.emergency_pause_bot(request.reason)


@router.post("/execution/emergency-stop")
def execution_emergency_stop(request: EmergencyRequest) -> dict:
    """Stop the paper bot through emergency controls."""
    return _emergency_controls.emergency_stop_bot(request.reason)


@router.post("/execution/emergency-cancel-dry-run")
def execution_emergency_cancel_dry_run(request: EmergencyRequest) -> dict:
    """Preview emergency live-order cancel without touching an exchange."""
    return _emergency_controls.emergency_cancel_live_orders_dry_run(request.reason)
