"""HTTP API routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.bot.paper_trading_bot import PaperTradingBotError
from app.alerts.alert_service import AlertService
from app.backtesting.backtest_engine import BacktestDataError, BacktestEngine
from app.calibration.strategy_calibration_report import StrategyCalibrationReportBuilder
from app.calibration.strategy_decision_gate import StrategyDecisionGate
from app.config import get_settings
from app.connectors.moomoo.moomoo_config import get_moomoo_config
from app.connectors.moomoo.moomoo_market_data import MooMooMarketData
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.execution.order_intent import OrderIntent
from app.core.app_state import AppState
from app.core.dependencies import (
    dependency_status,
    get_account_service,
    get_dashboard_service,
    get_dry_run_executor,
    get_emergency_controls,
    get_execution_guard,
    get_market_data_service,
    get_order_validator,
    get_paper_broker,
    get_paper_trading_bot,
    get_risk_manager,
    get_trade_executor,
    get_trade_journal,
)
from app.core.safety_audit import SafetyAudit
from app.diagnostics.calibration_report import CalibrationReport
from app.diagnostics.smoke_test_runner import SmokeTestRunner
from app.exchanges.kraken_adapter import EmptyMarketDataError, InvalidSymbolError, KrakenRequestError, UnsupportedTimeframeError
from app.journal.journal_hygiene import JournalHygiene
from app.observation.clean_observation_verifier import CleanObservationVerifier
from app.observation.controlled_paper_models import ControlledPaperObservationRequest
from app.observation.controlled_paper_audit import ControlledPaperAuditService
from app.observation.controlled_paper_observation import ControlledPaperObservationService
from app.observation.controlled_paper_preflight import ControlledPaperPreflightService
from app.observation.controlled_paper_preflight_review import ControlledPaperPreflightReviewService
from app.observation.controlled_paper_review import ControlledPaperReviewService
from app.observation.early_recovery import EarlyRecoveryClassifier
from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.observation.fresh_observation_validator import FreshObservationValidator
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_continuation import ObservationContinuationService
from app.observation.observation_readiness import ObservationReadinessChecker
from app.observation.observation_session import ObservationSessionManager
from app.observation.paper_observation_engine import PaperObservationEngine
from app.observation.paper_trade_approval_gate import PaperTradeApprovalGate
from app.observation.paper_trade_readiness import PaperTradeReadinessService
from app.observation.signal_quality_review import SignalQualityReviewService
from app.operator.operator_service import OperatorService
from app.risk.risk_readiness import RiskReadiness
from app.risk.risk_record_hygiene import RiskRecordHygiene
from app.storage.database import init_db
from app.stock_hunter.stock_hunter_service import StockHunterService
from app.reporting.unified_report_service import UnifiedReportService
from app.stock_hunter.options_strategy_models import OptionsScanRequest
from app.strategies.indicator_engine import IndicatorEngineError
from app.strategies.signal_scoring import SignalScoringError
from app.validation.real_data_validator import RealDataValidator

import pandas as pd

router = APIRouter()
_app_state = AppState()
_paper_observation_engine = PaperObservationEngine(settings=get_settings())
_observation_session_manager = ObservationSessionManager(_paper_observation_engine, settings=get_settings())


class PaperOrderRequest(BaseModel):
    """Request body for manual paper market orders."""

    symbol: str
    side: str
    quantity: float = Field(gt=0)
    market_price: float = Field(gt=0)
    reason: str | None = None


class ControlledPaperRequestBody(BaseModel):
    """Request body for controlled paper observation."""

    manual_start: bool = False
    operator_acknowledged: bool = False
    allow_paper_trade_preview: bool = True
    allow_paper_trade_execution: bool = False
    symbols: list[str] = Field(default_factory=list)
    timeframe: str = "1h"
    max_trades: int | None = None
    reason: str = "controlled paper observation"

    def to_request(self) -> ControlledPaperObservationRequest:
        """Convert to service request."""
        return ControlledPaperObservationRequest(**self.model_dump())


class OptionsScannerRequestBody(BaseModel):
    """Request body for read-only options scanner."""

    symbols: list[str] = Field(default_factory=list)
    option_type: str = "call"
    min_volume: int | None = None
    min_open_interest: int | None = None
    max_spread_pct: float | None = None
    delta_min: float | None = None
    delta_max: float | None = None
    min_dte: int | None = None
    max_dte: int | None = None
    target_dte_min: int | None = None
    target_dte_max: int | None = None
    top_n: int | None = None
    include_rejected: bool = False


class ObservationRunRequest(BaseModel):
    """Request body for manual paper observation run."""

    manual_run: bool = True
    allow_paper_trades: bool = False


class ObservationWindowStartRequest(BaseModel):
    """Request body for starting an observation window."""

    target_runs: int | None = Field(default=None, ge=1)
    allow_paper_trades: bool = False


class ObservationWindowRunRequest(BaseModel):
    """Request body for running the next observation window pass."""

    manual_run: bool = True
    ignore_interval: bool = False


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
        return {"symbols": get_market_data_service().get_symbols()}
    except KrakenRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/market/ticker/{symbol}")
def market_ticker(symbol: str) -> dict:
    """Return ticker data for a FastAPI-safe symbol such as BTC-USD."""
    try:
        return get_market_data_service().get_symbol_ticker(symbol)
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
        return {"candles": get_market_data_service().get_symbol_candles(symbol, timeframe=timeframe, limit=limit)}
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
        service = get_market_data_service()
        candles = pd.DataFrame(service.get_symbol_candles(symbol, timeframe=timeframe, limit=limit))
        normalized_symbol = symbol.strip().upper().replace("-", "/")
        return get_paper_trading_bot().strategy.evaluate(candles, symbol=normalized_symbol, timeframe=timeframe).to_dict()
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
    return get_paper_broker().get_account_summary()


@router.get("/paper/positions")
def paper_positions() -> dict:
    """Return open paper positions."""
    return {"positions": get_paper_broker().get_positions()}


@router.get("/paper/orders")
def paper_orders() -> dict:
    """Return paper orders."""
    return {"orders": get_paper_broker().get_orders()}


@router.get("/paper/fills")
def paper_fills() -> dict:
    """Return paper fills."""
    return {"fills": get_paper_broker().get_fills()}


@router.post("/paper/order")
def paper_order(request: PaperOrderRequest) -> dict:
    """Simulate a paper market order only."""
    return get_trade_executor().execute_paper_market_order(
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        market_price=request.market_price,
        reason=request.reason,
    )


@router.post("/paper/close/{symbol}")
def paper_close(symbol: str, request: PaperCloseRequest) -> dict:
    """Close a paper position using an explicit market price."""
    return get_trade_executor().close_paper_position(symbol, market_price=request.market_price, reason=request.reason)


@router.post("/paper/reset")
def paper_reset() -> dict:
    """Reset the in-memory paper account."""
    return get_paper_broker().reset()


@router.get("/risk/status")
def risk_status() -> dict:
    """Return risk manager status."""
    risk_manager = get_risk_manager()
    return {
        "kill_switch": risk_manager.kill_switch.status(),
        "settings": {
            "max_risk_per_trade": risk_manager.settings.max_risk_per_trade,
            "max_daily_loss": risk_manager.settings.max_daily_loss,
            "max_open_positions": risk_manager.settings.max_open_positions,
            "max_position_allocation": risk_manager.settings.max_position_allocation,
            "min_signal_score_to_trade": risk_manager.settings.min_signal_score_to_trade,
            "max_spread_bps": risk_manager.settings.max_spread_bps,
        },
    }


@router.post("/risk/evaluate")
def risk_evaluate(request: RiskEvaluateRequest) -> dict:
    """Evaluate risk only; do not execute trades."""
    account_summary = request.account_summary or get_paper_broker().get_account_summary()
    open_positions = request.open_positions if request.open_positions is not None else get_paper_broker().get_positions()
    decision = get_risk_manager().evaluate_trade(
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
    get_risk_manager().kill_switch.activate(request.reason or "manual activation")
    return get_risk_manager().kill_switch.status()


@router.post("/risk/kill-switch/deactivate")
def risk_kill_switch_deactivate(request: KillSwitchRequest) -> dict:
    """Deactivate the risk kill switch."""
    get_risk_manager().kill_switch.deactivate(request.reason)
    return get_risk_manager().kill_switch.status()


@router.get("/bot/status")
def bot_status() -> dict:
    """Return paper bot status."""
    return get_paper_trading_bot().status()


@router.post("/bot/start")
def bot_start(request: BotStartRequest) -> dict:
    """Start the paper bot without launching a blocking loop."""
    try:
        return get_paper_trading_bot().start(manual_start=request.manual_start)
    except PaperTradingBotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bot/stop")
def bot_stop() -> dict:
    """Stop the paper bot."""
    return get_paper_trading_bot().stop()


@router.post("/bot/pause")
def bot_pause() -> dict:
    """Pause the paper bot."""
    return get_paper_trading_bot().pause()


@router.post("/bot/resume")
def bot_resume() -> dict:
    """Resume the paper bot."""
    return get_paper_trading_bot().resume()


@router.post("/bot/scan-once")
def bot_scan_once() -> dict:
    """Run one manual paper scan."""
    try:
        return get_paper_trading_bot().scan_once()
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
    return {"events": get_trade_journal().get_recent_bot_events(limit=limit)}


@router.get("/journal/signals")
def journal_signals(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent signal records."""
    return {"signals": get_trade_journal().get_recent_signals(limit=limit, symbol=symbol)}


@router.get("/journal/risk-decisions")
def journal_risk_decisions(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent risk decision records."""
    return {"risk_decisions": get_trade_journal().get_recent_risk_decisions(limit=limit, symbol=symbol)}


@router.get("/journal/orders")
def journal_orders(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent paper orders."""
    return {"orders": get_trade_journal().get_recent_orders(limit=limit, symbol=symbol)}


@router.get("/journal/fills")
def journal_fills(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent paper fills."""
    return {"fills": get_trade_journal().get_recent_fills(limit=limit, symbol=symbol)}


@router.get("/journal/positions")
def journal_positions(symbol: str | None = None) -> dict:
    """Return recent paper position snapshots."""
    return {"positions": get_trade_journal().get_recent_positions(symbol=symbol)}


@router.get("/journal/account-snapshots")
def journal_account_snapshots(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return recent account snapshots."""
    return {"account_snapshots": get_trade_journal().get_recent_account_snapshots(limit=limit)}


@router.get("/journal/scans")
def journal_scans(limit: int = Query(default=50, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return recent scan results."""
    return {"scan_results": get_trade_journal().get_recent_scan_results(limit=limit, symbol=symbol)}


@router.get("/journal/errors")
def journal_errors(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return recent error records."""
    return {"errors": get_trade_journal().get_recent_errors(limit=limit)}


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
    return get_dashboard_service().get_overview().to_dict()


@router.get("/reports/paper-performance")
def report_paper_performance() -> dict:
    """Return read-only paper performance."""
    return get_dashboard_service().get_paper_performance().to_dict()


@router.get("/reports/signal-performance")
def report_signal_performance(limit: int = Query(default=100, ge=1, le=500), symbol: str | None = None) -> dict:
    """Return read-only signal performance."""
    report = get_dashboard_service().get_signal_performance(limit=limit).to_dict()
    if symbol:
        normalized = symbol.upper().replace("-", "/")
        report["recent_signals"] = [signal for signal in report["recent_signals"] if signal.get("symbol") == normalized]
        report["symbols_ranked_by_latest_score"] = [row for row in report["symbols_ranked_by_latest_score"] if row.get("symbol") == normalized]
    return report


@router.get("/reports/risk-summary")
def report_risk_summary() -> dict:
    """Return read-only risk summary."""
    return get_dashboard_service().get_risk_summary().to_dict()


@router.get("/reports/recent-activity")
def report_recent_activity(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return read-only recent activity."""
    return get_dashboard_service().get_recent_activity(limit=limit).to_dict()


@router.get("/reports/equity-curve")
def report_equity_curve(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return read-only equity curve."""
    return get_dashboard_service().get_equity_curve(limit=limit).to_dict()


@router.get("/reports/full-dashboard")
def report_full_dashboard() -> dict:
    """Return full read-only dashboard snapshot."""
    return get_dashboard_service().get_full_dashboard_snapshot()


@router.get("/reports/unified-summary")
def reports_unified_summary() -> dict:
    """Return read-only unified dashboard summary."""
    return UnifiedReportService(settings=get_settings()).get_unified_dashboard_summary()


@router.get("/reports/top-candidates")
def reports_top_candidates() -> dict:
    """Return read-only top candidates across crypto, stock, and options."""
    return UnifiedReportService(settings=get_settings()).get_top_candidates()


@router.get("/reports/daily-briefing")
def reports_daily_briefing() -> dict:
    """Return read-only daily briefing data."""
    return UnifiedReportService(settings=get_settings()).get_daily_briefing()


@router.get("/reports/system-health")
def reports_system_health() -> dict:
    """Return read-only system health summary."""
    return UnifiedReportService(settings=get_settings()).get_system_health_summary()


@router.get("/alerts/status")
def alerts_status() -> dict:
    """Return alert status without secrets."""
    return AlertService(settings=get_settings()).get_alert_status()


@router.get("/alerts/preview")
def alerts_preview() -> dict:
    """Preview alert report without external sends."""
    return AlertService(settings=get_settings()).preview_alert_report()


@router.post("/alerts/send-console")
def alerts_send_console() -> dict:
    """Send or block console alert according to read-only alert settings."""
    return AlertService(settings=get_settings()).send_console_alert()


@router.post("/alerts/send-discord-dry-run")
def alerts_send_discord_dry_run() -> dict:
    """Dry-run Discord alert without calling external webhooks."""
    return AlertService(settings=get_settings()).send_discord_alert_dry_run()


@router.get("/account/status")
def account_status() -> dict:
    """Return read-only Kraken private account connectivity status."""
    return get_account_service().get_status()


@router.get("/account/balances")
def account_balances() -> dict:
    """Return read-only Kraken balances or safe disabled response."""
    summary = get_account_service().get_account_summary()
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
    return get_account_service().get_account_summary().to_dict()


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
    return get_execution_guard().get_execution_safety_status()


@router.post("/execution/validate-order")
def execution_validate_order(request: ExecutionOrderRequest) -> dict:
    """Validate an order intent without placing an order."""
    intent = _build_order_intent(request)
    result = get_order_validator().validate_order_intent(
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
    validation = get_order_validator().validate_order_intent(
        intent,
        request.risk_decision,
        account_summary=request.account_summary,
        ticker=request.ticker,
        asset_pair_constraints=request.asset_pair_constraints,
    )
    return get_dry_run_executor().execute_dry_run(intent, validation)


@router.get("/execution/dry-runs")
def execution_dry_runs(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return recent dry-run order previews."""
    return {"dry_runs": get_dry_run_executor().get_recent_dry_runs(limit=limit)}


@router.post("/execution/emergency-pause")
def execution_emergency_pause(request: EmergencyRequest) -> dict:
    """Pause the paper bot through emergency controls."""
    return get_emergency_controls().emergency_pause_bot(request.reason)


@router.post("/execution/emergency-stop")
def execution_emergency_stop(request: EmergencyRequest) -> dict:
    """Stop the paper bot through emergency controls."""
    return get_emergency_controls().emergency_stop_bot(request.reason)


@router.post("/execution/emergency-cancel-dry-run")
def execution_emergency_cancel_dry_run(request: EmergencyRequest) -> dict:
    """Preview emergency live-order cancel without touching an exchange."""
    return get_emergency_controls().emergency_cancel_live_orders_dry_run(request.reason)


@router.get("/system/runtime")
def system_runtime() -> dict:
    """Return read-only runtime state without secrets."""
    return _app_state.get_runtime_summary()


@router.get("/system/dependencies")
def system_dependencies() -> dict:
    """Return shared dependency consistency status."""
    return dependency_status()


@router.get("/system/safety-audit")
def system_safety_audit() -> dict:
    """Run a read-only safety audit."""
    return SafetyAudit(settings=get_settings()).run().to_dict()


@router.get("/operator/status")
def operator_status() -> dict:
    """Return standalone operator status."""
    return OperatorService(settings=get_settings()).get_operator_status()


@router.get("/operator/startup-checks")
def operator_startup_checks() -> dict:
    """Run standalone startup checks."""
    return OperatorService(settings=get_settings()).run_startup_checks()


@router.get("/operator/commands")
def operator_commands() -> dict:
    """Return safe local operator commands."""
    return OperatorService(settings=get_settings()).get_safe_command_summary()


@router.get("/operator/daily-briefing")
def operator_daily_briefing() -> dict:
    """Return daily operator briefing."""
    return OperatorService(settings=get_settings()).get_daily_operator_briefing()


@router.get("/operator/next-actions")
def operator_next_actions() -> dict:
    """Return next recommended operator actions."""
    return {"actions": OperatorService(settings=get_settings()).get_next_recommended_actions(), "source": "crypto_hunter_operator_next_actions_v1"}


@router.get("/validation/status")
def validation_status() -> dict:
    """Return read-only validation configuration status."""
    settings = get_settings()
    return {
        "enabled": settings.real_data_validation_enabled,
        "read_only": settings.real_data_validation_read_only,
        "crypto_symbols": settings.validation_symbols_crypto,
        "stock_symbols": settings.validation_symbols_stock,
        "source": "crypto_hunter_validation_status_v1",
    }


@router.get("/validation/run")
def validation_run() -> dict:
    """Run all read-only real-data validation checks."""
    return RealDataValidator(settings=get_settings()).run_all_checks()


@router.get("/validation/kraken")
def validation_kraken() -> dict:
    """Run read-only Kraken public validation."""
    validator = RealDataValidator(settings=get_settings())
    checks = [validator.validate_safety_audit(), validator.validate_kraken_public_data(), validator.validate_crypto_signals()]
    from app.validation.validation_report import build_validation_report

    return build_validation_report(checks).to_dict()


@router.get("/validation/moomoo")
def validation_moomoo() -> dict:
    """Run read-only MooMoo validation."""
    validator = RealDataValidator(settings=get_settings())
    checks = [validator.validate_moomoo_health(), validator.validate_stock_hunter(), validator.validate_options_scanner()]
    from app.validation.validation_report import build_validation_report

    return build_validation_report(checks).to_dict()


@router.get("/validation/report")
def validation_report() -> dict:
    """Return full read-only validation report."""
    return RealDataValidator(settings=get_settings()).run_all_checks()


@router.get("/journal/hygiene/summary")
def journal_hygiene_summary(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return preview-only journal hygiene summary."""
    return JournalHygiene(get_trade_journal()).summarize_test_records(limit=limit)


@router.get("/journal/hygiene/test-records")
def journal_hygiene_test_records(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return detected fake/test/demo journal records."""
    records = JournalHygiene(get_trade_journal()).detect_test_records(limit=limit)
    return {"records": records, "count": len(records), "preview_only": True, "source": "crypto_hunter_journal_test_records_v1"}


@router.get("/journal/hygiene/production-preview")
def journal_hygiene_production_preview(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return production-style records without deleting anything."""
    return JournalHygiene(get_trade_journal()).production_preview(limit=limit)


@router.get("/observation/readiness")
def observation_readiness() -> dict:
    """Return readiness for long-running paper observation mode."""
    return ObservationReadinessChecker().check()


@router.get("/observation/status")
def observation_status() -> dict:
    """Return paper observation status."""
    return _paper_observation_engine.get_status()


@router.post("/observation/run-once")
def observation_run_once(request: ObservationRunRequest) -> dict:
    """Run one paper-only observation pass."""
    return _paper_observation_engine.run_once(manual_run=request.manual_run, allow_paper_trades=request.allow_paper_trades)


@router.get("/observation/recent")
def observation_recent(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    """Return recent observation runs."""
    return _paper_observation_engine.get_recent_observations(limit=limit)


@router.get("/observation/report")
def observation_report(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    """Return observation report."""
    runs = _observation_runs_for_reports(limit=limit)
    if runs:
        from app.observation.observation_report import build_observation_report

        report = build_observation_report(runs, limit=limit).to_dict()
        report["history_source"] = "memory_or_persisted"
        return report
    return _paper_observation_engine.get_observation_report(limit=limit)


@router.get("/calibration/status")
def calibration_status() -> dict:
    """Return read-only strategy calibration status."""
    settings = get_settings()
    return {
        "enabled": settings.calibration_enabled,
        "read_only": settings.calibration_read_only,
        "auto_apply_allowed": settings.calibration_allow_auto_apply,
        "min_observation_runs": settings.calibration_min_observation_runs,
        "min_sample_size_for_changes": settings.calibration_min_sample_size_for_changes,
        "recent_observation_runs": len(_paper_observation_engine.recent_runs),
        "persisted_history": ObservationHydrationService(settings=settings).history_summary(limit=settings.observation_history_limit),
        "source": "crypto_hunter_calibration_status_v1",
    }


@router.get("/calibration/report")
def calibration_report() -> dict:
    """Return read-only strategy calibration report."""
    return StrategyCalibrationReportBuilder(settings=get_settings()).build(_observation_runs_for_reports())


@router.get("/calibration/symbol/{symbol}")
def calibration_symbol(symbol: str) -> dict:
    """Return read-only strategy calibration summary for one symbol."""
    return StrategyCalibrationReportBuilder(settings=get_settings()).build_for_symbol(symbol, _observation_runs_for_reports())


@router.get("/calibration/recommendations")
def calibration_recommendations() -> dict:
    """Return read-only strategy threshold recommendations."""
    report = StrategyCalibrationReportBuilder(settings=get_settings()).build(_observation_runs_for_reports())
    return {
        "threshold_recommendations": report["threshold_recommendations"],
        "findings": report["findings"],
        "auto_apply_allowed": False,
        "source": "crypto_hunter_calibration_recommendations_v1",
    }


@router.get("/observation/window/status")
def observation_window_status() -> dict:
    """Return paper observation window status."""
    return _observation_session_manager.get_session_status()


@router.post("/observation/window/start")
def observation_window_start(request: ObservationWindowStartRequest) -> dict:
    """Start a manual observation window without running a background loop."""
    return _observation_session_manager.start_session(target_runs=request.target_runs, allow_paper_trades=request.allow_paper_trades)


@router.post("/observation/window/run-next")
def observation_window_run_next(request: ObservationWindowRunRequest) -> dict:
    """Run the next observation window pass manually."""
    return _observation_session_manager.run_next_observation(manual_run=request.manual_run, ignore_interval=request.ignore_interval)


@router.post("/observation/window/stop")
def observation_window_stop() -> dict:
    """Stop the active observation window."""
    return _observation_session_manager.stop_session()


@router.get("/observation/window/summary")
def observation_window_summary() -> dict:
    """Return current observation window summary."""
    return _observation_session_manager.get_window_summary()


@router.post("/observation/window/reset")
def observation_window_reset() -> dict:
    """Reset observation window state."""
    return _observation_session_manager.reset_session()


def _decision_runs() -> list[dict]:
    """Return the best available observation runs for decision endpoints."""
    if _observation_session_manager.session_runs:
        return _observation_session_manager.session_runs
    if _paper_observation_engine.recent_runs:
        return _paper_observation_engine.recent_runs
    settings = get_settings()
    if settings.observation_decision_gate_use_persisted_history:
        return ObservationHydrationService(settings=settings).load_recent_runs(limit=settings.observation_history_limit)
    return []


def _observation_runs_for_reports(limit: int | None = None, include_refused: bool = False) -> list[dict]:
    """Return observation runs from memory, falling back to persisted history."""
    if _observation_session_manager.session_runs:
        runs = _observation_session_manager.session_runs
    elif _paper_observation_engine.recent_runs:
        runs = _paper_observation_engine.recent_runs
    else:
        runs = ObservationHydrationService(settings=get_settings()).load_recent_runs(limit=limit, include_refused=include_refused)
    if include_refused:
        return runs[:limit] if limit else runs
    completed = [run for run in runs if run.get("status", "completed") == "completed"]
    return completed[:limit] if limit else completed


@router.get("/observation/decision-gate")
def observation_decision_gate() -> dict:
    """Return read-only observation strategy decision gate."""
    return StrategyDecisionGate(settings=get_settings(), safety_audit=SafetyAudit(settings=get_settings())).evaluate(_decision_runs()).to_dict()


@router.get("/observation/early-recovery")
def observation_early_recovery() -> dict:
    """Return observation-only early recovery candidates."""
    candidates = EarlyRecoveryClassifier(settings=get_settings()).classify_runs(_decision_runs())
    return {
        "enabled": get_settings().early_recovery_watchlist_enabled,
        "candidates": [candidate.to_dict() for candidate in candidates],
        "action": "OBSERVE_ONLY",
        "source": "crypto_hunter_early_recovery_candidates_v1",
    }


@router.get("/observation/early-recovery/watchlist")
def observation_early_recovery_watchlist() -> dict:
    """Return ranked observation-only early recovery watchlist."""
    return EarlyRecoveryWatchlistService(settings=get_settings(), runs=_decision_runs()).get_watchlist()


@router.get("/observation/early-recovery/report")
def observation_early_recovery_report() -> dict:
    """Return observation-only early recovery watchlist report."""
    return EarlyRecoveryWatchlistService(settings=get_settings(), runs=_decision_runs()).get_report()


@router.get("/observation/early-recovery/{symbol}")
def observation_early_recovery_symbol(symbol: str) -> dict:
    """Return one observation-only early recovery watchlist item."""
    return EarlyRecoveryWatchlistService(settings=get_settings(), runs=_decision_runs()).explain_candidate(symbol)


@router.get("/observation/history")
def observation_history(limit: int = Query(default=500, ge=1, le=5000), include_refused: bool = False) -> dict:
    """Return persisted observation history status and hydrated runs."""
    service = ObservationHydrationService(settings=get_settings())
    runs = service.load_recent_runs(limit=limit, include_refused=include_refused)
    return {"runs": runs, "count": len(runs), "history_source": "persisted", "source": "crypto_hunter_observation_history_v1"}


@router.get("/observation/history/runs")
def observation_history_runs(limit: int = Query(default=500, ge=1, le=5000), include_refused: bool = False) -> dict:
    """Return persisted observation runs."""
    runs = ObservationHydrationService(settings=get_settings()).load_recent_runs(limit=limit, include_refused=include_refused)
    return {"runs": runs, "count": len(runs), "history_source": "persisted", "source": "crypto_hunter_observation_history_runs_v1"}


@router.get("/observation/history/results")
def observation_history_results(limit: int = Query(default=500, ge=1, le=5000), include_refused: bool = False) -> dict:
    """Return persisted observation results."""
    results = ObservationHydrationService(settings=get_settings()).load_recent_results(limit=limit, include_refused=include_refused)
    return {"results": results, "count": len(results), "history_source": "persisted", "source": "crypto_hunter_observation_history_results_v1"}


@router.get("/observation/history/summary")
def observation_history_summary(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return persisted observation history summary."""
    return ObservationHydrationService(settings=get_settings()).history_summary(limit=limit)


@router.get("/observation/paper-trade-readiness")
def observation_paper_trade_readiness() -> dict:
    """Return read-only paper-trade observation readiness."""
    return PaperTradeReadinessService(settings=get_settings()).check()


@router.get("/observation/paper-trade-approval")
def observation_paper_trade_approval() -> dict:
    """Return paper-trade observation approval gate."""
    return PaperTradeApprovalGate(settings=get_settings()).evaluate()


@router.get("/observation/paper-trade-approval/checks")
def observation_paper_trade_approval_checks() -> dict:
    """Return paper-trade approval checks."""
    return PaperTradeApprovalGate(settings=get_settings()).checks()


@router.get("/observation/paper-trade-approval/package")
def observation_paper_trade_approval_package() -> dict:
    """Return paper-trade approval review package."""
    return PaperTradeApprovalGate(settings=get_settings()).package()


@router.get("/observation/clean-verification")
def observation_clean_verification() -> dict:
    """Return clean post-remediation observation verification."""
    return CleanObservationVerifier(settings=get_settings()).verify()


@router.get("/observation/fresh-validation")
def observation_fresh_validation() -> dict:
    """Return fresh observation validation."""
    return FreshObservationValidator(settings=get_settings()).validate()


@router.get("/observation/fresh-validation/runs")
def observation_fresh_validation_runs() -> dict:
    """Return fresh observation run summaries."""
    return FreshObservationValidator(settings=get_settings()).run_summaries()


@router.get("/observation/fresh-validation/readiness")
def observation_fresh_validation_readiness() -> dict:
    """Return compact fresh observation readiness."""
    return FreshObservationValidator(settings=get_settings()).readiness()


@router.get("/risk/hygiene/summary")
def risk_hygiene_summary(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return preview-only risk record hygiene summary."""
    return RiskRecordHygiene(get_trade_journal()).summary(limit=limit)


@router.get("/risk/hygiene/inconsistencies")
def risk_hygiene_inconsistencies(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return preview-only risk record inconsistencies."""
    inconsistencies = RiskRecordHygiene(get_trade_journal()).scan_records(limit=limit)
    return {"inconsistencies": [item.to_dict() for item in inconsistencies], "count": len(inconsistencies), "preview_only": True, "source": "crypto_hunter_risk_inconsistencies_v1"}


@router.get("/risk/hygiene/classification")
def risk_hygiene_classification(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return preview-only risk record classifications."""
    hygiene = RiskRecordHygiene(get_trade_journal())
    records = get_trade_journal().get_recent_risk_decisions(limit=limit)
    return {
        "classification": [hygiene.classify_risk_record(record) for record in records],
        "summary": hygiene.summarize_by_classification(records),
        "preview_only": True,
        "source": "crypto_hunter_risk_hygiene_classification_v1",
    }


@router.get("/risk/hygiene/remediation-preview")
def risk_hygiene_remediation_preview(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return read-only risk hygiene remediation preview."""
    return RiskRecordHygiene(get_trade_journal()).preview_remediation_plan(limit=limit)


@router.get("/risk/hygiene/recent-cleanliness")
def risk_hygiene_recent_cleanliness(limit: int = Query(default=100, ge=1, le=5000)) -> dict:
    """Return recent risk record cleanliness check."""
    return RiskRecordHygiene(get_trade_journal()).validate_recent_records_only(limit=limit)


@router.get("/risk/hygiene/legacy-aware-readiness")
def risk_hygiene_legacy_aware_readiness(limit: int = Query(default=100, ge=1, le=5000)) -> dict:
    """Return legacy-aware risk readiness."""
    return RiskRecordHygiene(get_trade_journal()).legacy_aware_readiness(limit=limit)


@router.get("/risk/readiness")
def risk_readiness(limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    """Return read-only risk readiness."""
    return RiskReadiness(RiskRecordHygiene(get_trade_journal())).check(limit=limit)


@router.get("/operator/fresh-observation-check")
def operator_fresh_observation_check() -> dict:
    """Return operator fresh observation check."""
    return FreshObservationValidator(settings=get_settings()).validate()


@router.get("/operator/paper-trade-approval-review")
def operator_paper_trade_approval_review() -> dict:
    """Return operator paper-trade approval review package."""
    return PaperTradeApprovalGate(settings=get_settings()).package()


@router.get("/observation/controlled-paper/status")
def controlled_paper_status() -> dict:
    """Return controlled paper observation status."""
    return ControlledPaperObservationService(settings=get_settings()).status()


@router.post("/observation/controlled-paper/evaluate")
def controlled_paper_evaluate(request: ControlledPaperRequestBody) -> dict:
    """Evaluate controlled paper observation gates."""
    return ControlledPaperObservationService(settings=get_settings()).evaluate(request.to_request())


@router.post("/observation/controlled-paper/preview")
def controlled_paper_preview(request: ControlledPaperRequestBody) -> dict:
    """Create controlled paper previews only."""
    return ControlledPaperObservationService(settings=get_settings()).preview(request.to_request())


@router.post("/observation/controlled-paper/run-once")
def controlled_paper_run_once(request: ControlledPaperRequestBody) -> dict:
    """Run controlled paper observation once."""
    return ControlledPaperObservationService(settings=get_settings()).run_once(request.to_request())


@router.get("/observation/controlled-paper/recent")
def controlled_paper_recent() -> dict:
    """Return recent controlled paper observation runs."""
    return ControlledPaperObservationService(settings=get_settings()).recent()


@router.get("/observation/controlled-paper/review")
def controlled_paper_review() -> dict:
    """Return controlled paper review report."""
    return ControlledPaperReviewService(settings=get_settings()).review()


@router.get("/observation/controlled-paper/audit")
def controlled_paper_audit() -> dict:
    """Return controlled paper guardrail audit."""
    return ControlledPaperAuditService(settings=get_settings()).audit()


@router.get("/observation/controlled-paper/guardrails")
def controlled_paper_guardrails() -> dict:
    """Return compact controlled paper guardrails."""
    return ControlledPaperAuditService(settings=get_settings()).guardrails()


@router.get("/operator/controlled-paper-observation")
def operator_controlled_paper_observation() -> dict:
    """Return operator controlled paper observation status."""
    service = ControlledPaperObservationService(settings=get_settings())
    return {"status": service.status(), "evaluation": service.evaluate(), "source": "crypto_hunter_operator_controlled_paper_observation_v1"}


@router.get("/operator/controlled-paper-review")
def operator_controlled_paper_review() -> dict:
    """Return operator controlled paper review and audit."""
    settings = get_settings()
    return {
        "review": ControlledPaperReviewService(settings=settings).review(),
        "audit": ControlledPaperAuditService(settings=settings).audit(),
        "source": "crypto_hunter_operator_controlled_paper_review_v1",
    }


@router.get("/observation/controlled-paper/preflight")
def controlled_paper_preflight() -> dict:
    """Return controlled paper activation preflight."""
    return ControlledPaperPreflightService(settings=get_settings()).evaluate()


@router.get("/observation/controlled-paper/preflight/checks")
def controlled_paper_preflight_checks() -> dict:
    """Return controlled paper preflight checks."""
    return ControlledPaperPreflightService(settings=get_settings()).checks()


@router.get("/observation/controlled-paper/activation-plan")
def controlled_paper_activation_plan() -> dict:
    """Return read-only controlled paper activation plan."""
    return ControlledPaperPreflightService(settings=get_settings()).activation_plan()


@router.get("/observation/controlled-paper/preflight-package")
def controlled_paper_preflight_package() -> dict:
    """Return complete controlled paper preflight package."""
    return ControlledPaperPreflightService(settings=get_settings()).package()


@router.get("/operator/controlled-paper-preflight")
def operator_controlled_paper_preflight() -> dict:
    """Return operator controlled paper preflight package."""
    return ControlledPaperPreflightService(settings=get_settings()).package()


@router.get("/observation/controlled-paper/decision")
def controlled_paper_decision() -> dict:
    """Return controlled paper preflight review decision."""
    return ControlledPaperPreflightReviewService(settings=get_settings()).decide()


@router.get("/observation/controlled-paper/decision/checks")
def controlled_paper_decision_checks() -> dict:
    """Return controlled paper decision checks."""
    return ControlledPaperPreflightReviewService(settings=get_settings()).checks()


@router.get("/observation/controlled-paper/decision-package")
def controlled_paper_decision_package() -> dict:
    """Return complete controlled paper decision package."""
    return ControlledPaperPreflightReviewService(settings=get_settings()).package()


@router.get("/operator/controlled-paper-decision")
def operator_controlled_paper_decision() -> dict:
    """Return operator controlled paper decision package."""
    return ControlledPaperPreflightReviewService(settings=get_settings()).package()


@router.get("/operator/controlled-paper-next-step")
def operator_controlled_paper_next_step() -> dict:
    """Return compact controlled paper next step."""
    return ControlledPaperPreflightReviewService(settings=get_settings()).next_step()


@router.get("/observation/signal-quality")
def observation_signal_quality() -> dict:
    """Return persisted observation signal quality review."""
    return SignalQualityReviewService(settings=get_settings()).review()


@router.get("/observation/signal-quality/symbols")
def observation_signal_quality_symbols() -> dict:
    """Return signal quality symbol summaries."""
    return SignalQualityReviewService(settings=get_settings()).symbols()


@router.get("/observation/signal-quality/{symbol}")
def observation_signal_quality_symbol(symbol: str) -> dict:
    """Return signal quality for one symbol."""
    return SignalQualityReviewService(settings=get_settings()).symbol(symbol)


@router.get("/observation/continuation-plan")
def observation_continuation_plan() -> dict:
    """Return safe observation continuation plan."""
    return ObservationContinuationService(settings=get_settings()).plan()


@router.get("/operator/signal-quality-review")
def operator_signal_quality_review() -> dict:
    """Return operator signal quality review."""
    return SignalQualityReviewService(settings=get_settings()).review()


@router.get("/operator/observation-next-step")
def operator_observation_next_step() -> dict:
    """Return compact operator observation next step."""
    plan = ObservationContinuationService(settings=get_settings()).plan()
    return {
        "decision": plan.get("decision"),
        "next_step": (plan.get("recommended_next_actions") or ["Continue observation-only mode."])[0],
        "paper_trades_allowed": False,
        "live_review_allowed": False,
        "source": "crypto_hunter_operator_observation_next_step_v1",
    }


@router.get("/calibration/decision-gate")
def calibration_decision_gate() -> dict:
    """Return read-only calibration decision gate."""
    return StrategyDecisionGate(settings=get_settings(), safety_audit=SafetyAudit(settings=get_settings())).evaluate(_decision_runs()).to_dict()


@router.get("/diagnostics/smoke-test")
def diagnostics_smoke_test() -> dict:
    """Run the Phase 14 safe local smoke test."""
    return SmokeTestRunner(settings=get_settings()).run()


@router.get("/diagnostics/calibration-report")
def diagnostics_calibration_report() -> dict:
    """Return a Phase 14 signal calibration report."""
    return CalibrationReport(settings=get_settings()).analyze_symbols()


@router.get("/moomoo/status")
def moomoo_status() -> dict:
    """Return safe MooMoo connector status without secrets."""
    config = get_moomoo_config(get_settings()).to_dict()
    health = MooMooReadOnlyClient(settings=get_settings()).get_health().to_dict()
    return {
        "config": config,
        "health": health,
        "trading_enabled": False,
        "read_only": config["read_only"],
        "source": "moomoo_readonly_status_v1",
    }


@router.get("/moomoo/health")
def moomoo_health() -> dict:
    """Return MooMoo import/OpenD health without unlocking trading."""
    return MooMooReadOnlyClient(settings=get_settings()).get_health().to_dict()


@router.get("/moomoo/capabilities")
def moomoo_capabilities() -> dict:
    """Return planned MooMoo read-only capabilities."""
    return MooMooReadOnlyClient(settings=get_settings()).get_supported_capabilities().to_dict()


@router.get("/moomoo/quote/{symbol}")
def moomoo_quote(symbol: str) -> dict:
    """Return read-only MooMoo quote data when available."""
    return MooMooMarketData(settings=get_settings()).get_quote_snapshot(symbol)


@router.get("/moomoo/candles/{symbol}")
def moomoo_candles(symbol: str, timeframe: str = Query(default="1d"), limit: int = Query(default=250, ge=1, le=5000)) -> dict:
    """Return read-only MooMoo candles when available."""
    return MooMooMarketData(settings=get_settings()).get_historical_candles(symbol, timeframe=timeframe, limit=limit)


@router.get("/moomoo/options/{symbol}")
def moomoo_options(symbol: str) -> dict:
    """Return read-only MooMoo option-chain data when available."""
    return MooMooMarketData(settings=get_settings()).get_option_chain(symbol)


@router.get("/stock-hunter/status")
def stock_hunter_status() -> dict:
    """Return read-only Stock/Options Hunter status."""
    return StockHunterService(settings=get_settings()).get_status()


@router.get("/stock-hunter/watchlist")
def stock_hunter_watchlist() -> dict:
    """Return Stock/Options Hunter watchlist."""
    return StockHunterService(settings=get_settings()).get_watchlist()


@router.get("/stock-hunter/scan")
def stock_hunter_scan() -> dict:
    """Scan stock watchlist without trading."""
    return StockHunterService(settings=get_settings()).scan_watchlist()


@router.get("/stock-hunter/top-candidates")
def stock_hunter_top_candidates(limit: int = Query(default=10, ge=1, le=100)) -> dict:
    """Return ranked read-only Stock/Options Hunter research candidates."""
    return StockHunterService(settings=get_settings()).top_candidates(limit=limit)


@router.get("/stock-hunter/analyze/{symbol}")
def stock_hunter_analyze(symbol: str) -> dict:
    """Analyze one stock/ETF symbol without trading."""
    return StockHunterService(settings=get_settings()).analyze_symbol(symbol)


@router.get("/stock-hunter/options/{symbol}")
def stock_hunter_options(symbol: str) -> dict:
    """Analyze options chain research candidates without execution."""
    return StockHunterService(settings=get_settings()).analyze_options(symbol)


@router.get("/options-scanner/status")
def options_scanner_status() -> dict:
    """Return dedicated read-only options scanner status."""
    return StockHunterService(settings=get_settings()).options_scanner_status()


@router.post("/options-scanner/scan")
def options_scanner_scan(body: OptionsScannerRequestBody) -> dict:
    """Run a read-only options scan without execution."""
    request = OptionsScanRequest(**body.model_dump())
    return StockHunterService(settings=get_settings()).scan_options(request)


@router.get("/options-scanner/top")
def options_scanner_top(limit: int = Query(default=10, ge=1, le=100)) -> dict:
    """Return top read-only option candidates from the default watchlist."""
    return StockHunterService(settings=get_settings()).top_options(limit=limit)
