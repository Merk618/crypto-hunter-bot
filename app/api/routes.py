"""HTTP API routes."""

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.data.market_data_service import MarketDataService
from app.exchanges.kraken_adapter import EmptyMarketDataError, InvalidSymbolError, KrakenRequestError, UnsupportedTimeframeError

router = APIRouter()


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
