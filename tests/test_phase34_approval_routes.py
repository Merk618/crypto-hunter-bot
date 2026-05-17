"""Phase 34 approval route tests."""

from app.main import app


def test_phase34_approval_routes_exist() -> None:
    """Approval route paths exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/paper-trade-approval" in paths
    assert "/observation/paper-trade-approval/checks" in paths
    assert "/observation/paper-trade-approval/package" in paths
    assert "/operator/paper-trade-approval-review" in paths


def test_phase34_approval_routes_do_not_expose_secrets() -> None:
    """Approval routes do not expose secret names."""
    paths = " ".join(route.path.lower() for route in app.routes if "approval" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
