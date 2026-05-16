"""Options scanner route and safety tests."""

import inspect

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.core.safety_audit import SafetyAudit
from app.main import app


def test_options_scanner_status_route_exists() -> None:
    """Status route is registered."""
    assert "/options-scanner/status" in {route.path for route in app.routes}


def test_options_scanner_scan_route_exists() -> None:
    """Scan route is registered."""
    assert "/options-scanner/scan" in {route.path for route in app.routes}


def test_options_scanner_top_route_exists() -> None:
    """Top route is registered."""
    assert "/options-scanner/top" in {route.path for route in app.routes}


def test_options_scanner_routes_do_not_expose_secrets() -> None:
    """Options scanner routes expose no secret-like paths."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/options-scanner"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "account" not in paths


def test_no_moomoo_order_cancel_unlock_methods_added() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_no_options_execution_routes_added() -> None:
    """Options scanner routes do not expose execution language."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "option-order" not in paths


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
