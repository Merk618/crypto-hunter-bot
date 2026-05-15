"""Market data response models."""

from datetime import datetime

from pydantic import BaseModel


class Candle(BaseModel):
    """Single OHLCV candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    vwap: float
    volume: float
    count: int
    symbol: str
    exchange_symbol: str


class Ticker(BaseModel):
    """Clean ticker data."""

    symbol: str
    exchange_symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    timestamp: str
    source: str
