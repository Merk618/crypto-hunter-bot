"""Market data service and route tests."""

import pandas as pd

from app.config import Settings
from app.data.market_data_service import MarketDataService
from app.main import app


class FakeExchange:
    """Fake exchange for service tests."""

    def get_symbols(self) -> list[str]:
        """Return fake symbols."""
        return ["BTC/USD", "ETH/USD"]

    def get_ticker(self, symbol: str) -> dict:
        """Return fake ticker data."""
        return {"symbol": symbol, "last": 100.0}

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Return fake candle data."""
        return pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp("2026-01-01T00:00:00Z"),
                    "open": 1.0,
                    "high": 2.0,
                    "low": 0.5,
                    "close": 1.5,
                    "vwap": 1.4,
                    "volume": 10.0,
                    "count": 3,
                    "symbol": symbol,
                    "exchange_symbol": symbol.replace("/", ""),
                }
            ]
        )


def test_market_data_service_uses_allowed_symbols() -> None:
    """Watchlist tickers are requested for configured allowed symbols."""
    settings = Settings(_env_file=None, ALLOWED_SYMBOLS="BTC/USD,ETH/USD")
    service = MarketDataService(exchange=FakeExchange(), settings=settings)  # type: ignore[arg-type]
    tickers = service.get_watchlist_tickers()
    assert [ticker["symbol"] for ticker in tickers] == ["BTC/USD", "ETH/USD"]


def test_market_data_service_converts_path_symbols() -> None:
    """Path-safe symbols convert internally to slash symbols."""
    service = MarketDataService(exchange=FakeExchange(), settings=Settings(_env_file=None))  # type: ignore[arg-type]
    ticker = service.get_symbol_ticker("BTC-USD")
    assert ticker["symbol"] == "BTC/USD"


def test_fastapi_market_routes_exist() -> None:
    """Market routes are registered on the FastAPI app."""
    paths = {route.path for route in app.routes}
    assert "/market/symbols" in paths
    assert "/market/ticker/{symbol}" in paths
    assert "/market/candles/{symbol}" in paths
