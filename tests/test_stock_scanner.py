"""Stock scanner tests."""

from app.config import Settings
from app.connectors.moomoo.moomoo_health import MooMooHealth
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.stock_hunter.stock_hunter_service import StockHunterService
from app.stock_hunter.stock_scanner import StockScanner


def disabled_client() -> MooMooReadOnlyClient:
    """Create disabled MooMoo client."""
    settings = Settings(_env_file=None)
    return MooMooReadOnlyClient(settings=settings, health_checker=MooMooHealth(settings, import_checker=lambda _: False))


def test_stock_scanner_handles_moomoo_disabled_cleanly() -> None:
    """Scanner returns no-action result when MooMoo is unavailable."""
    result = StockScanner(moomoo_client=disabled_client()).scan_symbol("AAPL")

    assert result.action == "NO_ACTION"
    assert "MooMoo read-only data unavailable" in result.blockers
    assert result.stock_signal is not None


def test_stock_hunter_service_status_returns_read_only() -> None:
    """Service status confirms read-only behavior."""
    service = StockHunterService(settings=Settings(_env_file=None), moomoo_client=disabled_client())
    status = service.get_status()

    assert status["read_only"] is True
    assert status["trading_allowed"] is False
