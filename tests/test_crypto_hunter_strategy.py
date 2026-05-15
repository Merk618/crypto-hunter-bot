"""Crypto Hunter strategy wrapper tests."""

import numpy as np
import pandas as pd

from app.main import app
from app.strategies.crypto_hunter_strategy import CryptoHunterStrategy
from app.strategies.signal_scoring import SignalResult


def raw_candles(rows: int = 260) -> pd.DataFrame:
    """Build raw candle data without indicators."""
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    close = np.linspace(100, 160, rows) + np.sin(np.arange(rows) / 4)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close - 0.5,
            "high": close + 1.5,
            "low": close - 1.5,
            "close": close,
            "vwap": close,
            "volume": 1000.0 + np.arange(rows),
            "count": np.arange(rows) + 1,
            "symbol": "BTC/USD",
            "exchange_symbol": "XXBTZUSD",
        }
    )


def test_crypto_hunter_strategy_adds_indicators_automatically() -> None:
    """Strategy accepts raw candles and returns a SignalResult."""
    result = CryptoHunterStrategy().evaluate(raw_candles(), symbol="BTC/USD", timeframe="1h")
    assert isinstance(result, SignalResult)
    assert result.symbol == "BTC/USD"
    assert result.source == "crypto_hunter_signal_v1"


def test_fastapi_signal_routes_exist() -> None:
    """Signal routes are registered."""
    paths = {route.path for route in app.routes}
    assert "/signals/{symbol}" in paths
    assert "/signals/watchlist" in paths


def test_no_live_order_execution_routes_added() -> None:
    """Signal routes do not expose live order routes."""
    paths = {route.path for route in app.routes}
    assert not any(path.startswith("/live") for path in paths)
