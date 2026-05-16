"""MooMoo route and safety tests."""

from app.core.safety_audit import SafetyAudit
from app.main import app


def test_moomoo_routes_exist() -> None:
    """MooMoo read-only routes are registered."""
    paths = {route.path for route in app.routes}

    assert "/moomoo/status" in paths
    assert "/moomoo/health" in paths
    assert "/moomoo/capabilities" in paths


def test_moomoo_routes_do_not_expose_secrets() -> None:
    """MooMoo route paths do not expose secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/moomoo"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "account_id" not in paths


def test_kraken_safety_audit_still_passes() -> None:
    """Adding MooMoo feasibility does not weaken Kraken safety audit."""
    report = SafetyAudit().run()

    assert report.passed is True
    assert report.live_trading_locked is True


def test_no_kraken_add_order_added() -> None:
    """Routes do not add Kraken live-order paths."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths


def test_no_withdrawals_transfers_funding_staking_routes_added() -> None:
    """Routes do not add fund-movement surfaces."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths


def test_no_live_trading_routes_added() -> None:
    """No live-trading route prefix is present."""
    paths = {route.path.lower() for route in app.routes}

    assert not any(path.startswith("/live") for path in paths)
