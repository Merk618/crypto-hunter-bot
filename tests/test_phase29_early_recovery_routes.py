"""Phase 29 early recovery route tests."""

from app.main import app


def test_early_recovery_watchlist_routes_exist() -> None:
    """Early recovery watchlist routes exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/early-recovery/watchlist" in paths
    assert "/observation/early-recovery/report" in paths
    assert "/observation/early-recovery/{symbol}" in paths


def test_early_recovery_routes_do_not_expose_secrets() -> None:
    """Early recovery routes expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if "early-recovery" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths

