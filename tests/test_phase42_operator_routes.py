"""Phase 42 operator route tests."""

from app.main import app


def test_phase42_operator_routes_exist() -> None:
    """Phase 42 route paths exist."""
    paths = {route.path for route in app.routes}

    assert "/operator/local-runbook" in paths
    assert "/operator/one-command-health-check" in paths
    assert "/operator/local-smoke-test" in paths
    assert "/operator/v1-startup-guide" in paths


def test_phase42_routes_do_not_expose_secrets() -> None:
    """Operator route paths do not expose secret names."""
    paths = " ".join(route.path.lower() for route in app.routes if "local-runbook" in route.path or "health-check" in route.path or "startup-guide" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
