"""Phase 18 stock scanner ranking tests."""

from app.config import Settings
from app.connectors.moomoo.moomoo_health import MooMooHealth
from app.connectors.moomoo.moomoo_market_data import MooMooMarketData
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app
from app.stock_hunter.stock_scanner import StockScanner


class RankedProvider:
    """Mock provider with different symbol strengths."""

    def get_quote_snapshot(self, provider_symbol: str) -> dict:
        """Return quote by symbol."""
        if provider_symbol.endswith("MSFT"):
            return {
                "latest_price": 90,
                "ema_20": 95,
                "ema_50": 100,
                "ema_200": 120,
                "rsi": 35,
                "macd_line": -1,
                "macd_signal": 1,
                "volume": 100_000,
                "avg_volume": 1_000_000,
                "momentum_5d": -2,
                "momentum_20d": -8,
                "previous_close": 92,
            }
        return {
            "latest_price": 150,
            "ema_20": 145,
            "ema_50": 135,
            "ema_200": 110,
            "rsi": 55,
            "macd_line": 3,
            "macd_signal": 1,
            "volume": 2_000_000,
            "avg_volume": 1_000_000,
            "momentum_5d": 2,
            "momentum_20d": 8,
            "previous_close": 148,
            "bid": 149.9,
            "ask": 150.1,
        }

    def get_historical_candles(self, provider_symbol: str, timeframe: str, limit: int) -> list[dict]:
        """Return minimal candle set."""
        return [{"timestamp": "2026-05-15", "open": 148, "high": 151, "low": 147, "close": 150, "volume": 2_000_000}]

    def get_option_chain(self, provider_symbol: str) -> list[dict]:
        """Return option contracts."""
        return [
            {
                "symbol": f"{provider_symbol}260619C00150000",
                "underlying": provider_symbol.replace("US.", ""),
                "expiration": "2026-06-19",
                "strike": 150,
                "option_type": "call",
                "bid": 4.95,
                "ask": 5.05,
                "last": 5,
                "volume": 5000,
                "open_interest": 8000,
                "delta": 0.55,
            }
        ]


def enabled_client() -> MooMooReadOnlyClient:
    """Create available read-only MooMoo client."""
    settings = Settings(_env_file=None, MOOMOO_ENABLED=True)
    health = MooMooHealth(settings, import_checker=lambda _: True, socket_checker=lambda host, port: True)
    md = MooMooMarketData(settings=settings, health_checker=health, provider=RankedProvider())
    return MooMooReadOnlyClient(settings=settings, health_checker=health, market_data=md)


def test_scanner_ranks_candidates_by_opportunity_score() -> None:
    """Scanner returns highest opportunity first."""
    results = StockScanner(moomoo_client=enabled_client()).scan(["MSFT", "AAPL"])

    assert results[0].symbol == "AAPL"
    assert results[0].rank == 1
    assert results[0].opportunity_score >= results[1].opportunity_score


def test_scanner_handles_moomoo_disabled_cleanly() -> None:
    """Disabled MooMoo produces no-action result."""
    settings = Settings(_env_file=None)
    health = MooMooHealth(settings, import_checker=lambda _: False)
    client = MooMooReadOnlyClient(settings=settings, health_checker=health)
    result = StockScanner(moomoo_client=client).scan_symbol("AAPL")

    assert result.action == "NO_ACTION"
    assert result.opportunity_score == 0
    assert result.blockers


def test_stock_hunter_top_candidates_route_exists() -> None:
    """Top candidates route is registered."""
    paths = {route.path for route in app.routes}

    assert "/stock-hunter/top-candidates" in paths
