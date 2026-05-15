"""HTTP API routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import get_settings
from app.data.market_data_service import MarketDataService
from app.execution.paper_broker import PaperBroker
from app.execution.trade_executor import TradeExecutor
from app.exchanges.kraken_adapter import EmptyMarketDataError, InvalidSymbolError, KrakenRequestError, UnsupportedTimeframeError
from app.strategies.crypto_hunter_strategy import CryptoHunterStrategy
from app.strategies.indicator_engine import IndicatorEngineError
from app.strategies.signal_scoring import SignalScoringError

import pandas as pd

router = APIRouter()
_paper_broker = PaperBroker()
_trade_executor = TradeExecutor(paper_broker=_paper_broker)


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
