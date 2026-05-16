"""Stock Hunter route and safety tests."""

import inspect

from app.core.safety_audit import SafetyAudit
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app


def test_stock_hunter_routes_exist() -> None:
    """Stock Hunter read-only routes are registered."""
    paths = {route.path for route in app.routes}

    assert "/stock-hunter/status" in paths
    assert "/stock-hunter/watchlist" in paths
    assert "/stock-hunter/scan" in paths
    assert "/stock-hunter/analyze/{symbol}" in paths
    assert "/stock-hunter/options/{symbol}" in paths


def test_stock_hunter_routes_do_not_expose_secrets() -> None:
    """Stock Hunter route names expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/stock-hunter"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "account" not in paths


def test_no_moomoo_order_or_options_execution_methods_added() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names
    assert "execute" not in names


def test_kraken_safety_audit_still_passes() -> None:
    """Kraken safety remains intact."""
    assert SafetyAudit().run().passed is True


def test_no_kraken_add_order_or_fund_movement_routes_added() -> None:
    """Routes do not expose live or fund movement paths."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
    assert not any(route.path.lower().startswith("/live") for route in app.routes)
