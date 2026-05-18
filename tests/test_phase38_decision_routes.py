"""Phase 38 controlled paper decision route tests."""

from app.main import app


def test_phase38_decision_routes_exist() -> None:
    """Decision route paths exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/controlled-paper/decision" in paths
    assert "/observation/controlled-paper/decision/checks" in paths
    assert "/observation/controlled-paper/decision-package" in paths
    assert "/operator/controlled-paper-decision" in paths
    assert "/operator/controlled-paper-next-step" in paths


def test_phase38_routes_do_not_expose_secrets() -> None:
    """Decision routes expose no secret names."""
    paths = " ".join(route.path.lower() for route in app.routes if "controlled-paper/decision" in route.path or "controlled-paper-next-step" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
