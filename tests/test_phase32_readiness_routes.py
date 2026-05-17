"""Phase 32 readiness route tests."""

from app.main import app


def test_phase32_routes_exist() -> None:
    """Phase 32 route paths exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/clean-verification" in paths
    assert "/risk/hygiene/legacy-aware-readiness" in paths
    assert "/risk/hygiene/recent-cleanliness" in paths
    assert "/observation/paper-trade-readiness" in paths


def test_phase32_routes_do_not_expose_secrets() -> None:
    """Phase 32 routes do not expose secret names."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith(("/observation/clean", "/risk/hygiene")))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
