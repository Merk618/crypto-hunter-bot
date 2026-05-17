"""Phase 31 risk hygiene route tests."""

from app.main import app


def test_phase31_risk_hygiene_routes_exist() -> None:
    """Phase 31 hygiene routes exist."""
    paths = {route.path for route in app.routes}

    assert "/risk/hygiene/classification" in paths
    assert "/risk/hygiene/remediation-preview" in paths
    assert "/risk/hygiene/recent-cleanliness" in paths


def test_phase31_risk_routes_do_not_expose_secrets() -> None:
    """Risk hygiene routes expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/risk/hygiene"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths

