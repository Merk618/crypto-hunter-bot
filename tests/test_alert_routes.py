"""Alert and unified report route tests."""

import inspect

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app


def test_alert_routes_exist() -> None:
    """Alert routes are registered."""
    paths = {route.path for route in app.routes}

    assert "/alerts/status" in paths
    assert "/alerts/preview" in paths
    assert "/alerts/send-console" in paths
    assert "/alerts/send-discord-dry-run" in paths


def test_unified_report_routes_exist() -> None:
    """Unified report routes are registered."""
    paths = {route.path for route in app.routes}

    assert "/reports/unified-summary" in paths
    assert "/reports/top-candidates" in paths
    assert "/reports/daily-briefing" in paths
    assert "/reports/system-health" in paths


def test_routes_do_not_expose_webhook_url_or_secrets() -> None:
    """Route paths expose no secret fields."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "webhook" not in paths
    assert "secret" not in paths
    assert "api_key" not in paths


def test_no_trading_methods_added_to_moomoo() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_no_forbidden_routes_added() -> None:
    """No execution or fund movement routes are added."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths
    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
