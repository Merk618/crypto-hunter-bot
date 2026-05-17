"""Phase 30 readiness route tests."""

from app.main import app


def test_paper_trade_readiness_routes_exist() -> None:
    """Readiness routes exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/paper-trade-readiness" in paths
    assert "/risk/hygiene/summary" in paths
    assert "/risk/hygiene/inconsistencies" in paths
    assert "/risk/readiness" in paths


def test_readiness_routes_do_not_expose_secrets() -> None:
    """Readiness routes expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if "readiness" in route.path or "hygiene" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths

