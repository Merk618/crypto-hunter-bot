"""MooMoo Stock Hunter integration tests."""

import inspect

from app.config import Settings
from app.connectors.moomoo.moomoo_health import MooMooHealth
from app.connectors.moomoo.moomoo_market_data import MooMooMarketData
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.core.safety_audit import SafetyAudit
from app.main import app
from app.stock_hunter.options_chain_analyzer import OptionsChainAnalyzer
from app.stock_hunter.stock_hunter_service import StockHunterService
from app.stock_hunter.stock_scanner import StockScanner

class FakeProvider:
    """Mock provider for Stock Hunter integration tests."""

    def get_quote_snapshot(self, provider_symbol: str) -> dict:
        """Return fake quote."""
        return {
            "latest_price": 200,
            "open": 190,
            "high": 205,
            "low": 188,
            "previous_close": 189,
            "volume": 2000000,
            "avg_volume": 1000000,
            "ema_20": 190,
            "ema_50": 180,
            "ema_200": 150,
            "rsi": 55,
            "macd_line": 3,
            "macd_signal": 1,
            "momentum_5d": 2,
            "momentum_20d": 8,
            "bid": 199.9,
            "ask": 200.1,
        }

    def get_historical_candles(self, provider_symbol: str, timeframe: str, limit: int) -> list[dict]:
        """Return fake candles."""
        return [
            {
                "timestamp": f"2026-01-{(idx % 28) + 1:02d}",
                "open": 120 + idx * 0.35,
                "high": 121 + idx * 0.35,
                "low": 119 + idx * 0.35,
                "close": 120 + idx * 0.4,
                "volume": 1000000 + idx * 1000,
            }
            for idx in range(220)
        ]

    def get_option_chain(self, provider_symbol: str) -> list[dict]:
        """Return fake option chain."""
        return [{"symbol": "US.AAPL260619C00200000", "underlying": "AAPL", "expiration": "2026-06-19", "strike": 200, "option_type": "call", "bid": 4.9, "ask": 5.1, "last": 5, "volume": 1000, "open_interest": 2000, "delta": 0.55}]


def enabled_client(provider=None) -> MooMooReadOnlyClient:
    """Create available read-only client with mocked data."""
    settings = Settings(_env_file=None, MOOMOO_ENABLED=True)
    health = MooMooHealth(settings, import_checker=lambda _: True, socket_checker=lambda host, port: True)
    md = MooMooMarketData(settings=settings, health_checker=health, provider=provider or FakeProvider())
    return MooMooReadOnlyClient(settings=settings, health_checker=health, market_data=md)


def test_stock_hunter_service_analyze_symbol_uses_moomoo_data_when_enabled() -> None:
    """Stock service uses mocked MooMoo data when available."""
    service = StockHunterService(settings=Settings(_env_file=None, MOOMOO_ENABLED=True), moomoo_client=enabled_client())
    result = service.analyze_symbol("AAPL")

    assert result["action"] == "RESEARCH_ONLY"
    assert result["stock_signal"]["latest_price"] == 200
    assert result["stock_signal"]["category"] in {"LEADING", "WATCH", "NEUTRAL", "WEAK", "AVOID"}


def test_stock_hunter_service_handles_data_unavailable_cleanly() -> None:
    """Disabled MooMoo returns DATA_UNAVAILABLE signal."""
    service = StockHunterService(settings=Settings(_env_file=None))
    result = service.analyze_symbol("AAPL")

    assert result["action"] == "NO_ACTION"
    assert result["stock_signal"]["trend_status"] == "DATA_UNAVAILABLE"


def test_stock_scanner_scans_watchlist_with_mocked_moomoo_data() -> None:
    """Scanner can scan multiple symbols using mocked data."""
    scanner = StockScanner(moomoo_client=enabled_client())
    results = scanner.scan(["AAPL", "MSFT"])

    assert len(results) == 2
    assert all(result.action == "RESEARCH_ONLY" for result in results)


def test_options_analyzer_receives_normalized_contracts() -> None:
    """Normalized MooMoo contracts feed the existing analyzer."""
    chain = enabled_client().get_option_chain("AAPL")
    analysis = OptionsChainAnalyzer(Settings(_env_file=None)).analyze("AAPL", chain["contracts"])

    assert analysis.contracts_analyzed == 1
    assert len(analysis.best_call_candidates) == 1


def test_moomoo_quote_candle_options_routes_exist() -> None:
    """Optional MooMoo market-data routes are registered."""
    paths = {route.path for route in app.routes}

    assert "/moomoo/quote/{symbol}" in paths
    assert "/moomoo/candles/{symbol}" in paths
    assert "/moomoo/options/{symbol}" in paths


def test_moomoo_market_data_routes_do_not_expose_secrets() -> None:
    """MooMoo route paths expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/moomoo"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "account" not in paths


def test_no_moomoo_order_cancel_unlock_methods_exist() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_kraken_safety_audit_still_passes() -> None:
    """Kraken safety remains intact."""
    assert SafetyAudit().run().passed is True


def test_no_kraken_add_order_or_fund_movement_routes_added() -> None:
    """Routes do not expose live order or fund movement paths."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
