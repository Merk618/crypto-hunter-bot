"""Kraken public data adapter tests with mocked responses."""

import pandas as pd
import pytest

from app.config import Settings
from app.exchanges.kraken_adapter import InvalidSymbolError, KrakenAdapter, UnsupportedTimeframeError


def asset_pairs_payload() -> dict:
    """Return mocked Kraken AssetPairs data."""
    return {
        "error": [],
        "result": {
            "XXBTZUSD": {"wsname": "XBT/USD", "base": "XXBT", "quote": "ZUSD", "status": "online"},
            "XETHZUSD": {"wsname": "ETH/USD", "base": "XETH", "quote": "ZUSD", "status": "online"},
            "SOLUSD": {"wsname": "SOL/USD", "base": "SOL", "quote": "ZUSD", "status": "online"},
        },
    }


def make_adapter() -> KrakenAdapter:
    """Create a Kraken adapter with mocked public requests."""
    adapter = KrakenAdapter(settings=Settings(_env_file=None))

    def fake_public_request(endpoint: str, params: dict | None = None) -> dict:
        if endpoint == "AssetPairs":
            return asset_pairs_payload()
        if endpoint == "Ticker":
            return {
                "error": [],
                "result": {
                    "XXBTZUSD": {
                        "a": ["101.0", "1", "1"],
                        "b": ["100.0", "1", "1"],
                        "c": ["100.5", "0.1"],
                        "v": ["10.0", "20.0"],
                    }
                },
            }
        if endpoint == "OHLC":
            return {
                "error": [],
                "result": {
                    "XXBTZUSD": [
                        [1700000060, "101", "102", "100", "101.5", "101.2", "2.5", 7],
                        [1700000000, "100", "101", "99", "100.5", "100.2", "1.5", 5],
                    ],
                    "last": 1700000060,
                },
            }
        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    adapter._public_request = fake_public_request  # type: ignore[method-assign]
    return adapter


def test_timeframe_conversion() -> None:
    """Supported timeframes convert to Kraken intervals."""
    adapter = make_adapter()
    assert adapter.timeframe_to_interval("1m") == 1
    assert adapter.timeframe_to_interval("1h") == 60
    assert adapter.timeframe_to_interval("1d") == 1440


def test_symbol_normalization_and_exchange_resolution() -> None:
    """Common symbols normalize and resolve to native Kraken names."""
    adapter = make_adapter()
    assert adapter.normalize_symbol("BTC-USD") == "BTC/USD"
    assert adapter.to_exchange_symbol("BTC/USD") == "XXBTZUSD"


def test_unsupported_timeframe_rejection() -> None:
    """Unsupported timeframes raise a clean custom error."""
    adapter = make_adapter()
    with pytest.raises(UnsupportedTimeframeError):
        adapter.timeframe_to_interval("2h")


def test_invalid_symbol_rejection() -> None:
    """Unavailable symbols raise a clean custom error."""
    adapter = make_adapter()
    with pytest.raises(InvalidSymbolError):
        adapter.to_exchange_symbol("DOGE/USD")


def test_candle_dataframe_shape_and_columns() -> None:
    """OHLC responses parse into a clean DataFrame."""
    adapter = make_adapter()
    df = adapter.get_candles("BTC/USD", timeframe="1h", limit=2)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "vwap",
        "volume",
        "count",
        "symbol",
        "exchange_symbol",
    ]
    assert len(df) == 2
    assert df.iloc[0]["open"] == 100.0
    assert df.iloc[0]["count"] == 5
    assert df.iloc[0]["symbol"] == "BTC/USD"


def test_ticker_parsing() -> None:
    """Ticker responses parse into a clean dictionary."""
    adapter = make_adapter()
    ticker = adapter.get_ticker("BTC/USD")
    assert ticker["symbol"] == "BTC/USD"
    assert ticker["exchange_symbol"] == "XXBTZUSD"
    assert ticker["bid"] == 100.0
    assert ticker["ask"] == 101.0
    assert ticker["last"] == 100.5
    assert ticker["volume"] == 20.0
    assert ticker["source"] == "kraken"
