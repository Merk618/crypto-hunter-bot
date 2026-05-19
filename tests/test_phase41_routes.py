"""Phase 41 route tests."""

from app.main import app


def test_phase41_audit_routes_exist() -> None:
    """Audit and operator routes exist."""
    paths = {route.path for route in app.routes}

    assert "/audit/standalone-readiness" in paths
    assert "/audit/final-safety-review" in paths
    assert "/audit/v1-completion-checklist" in paths
    assert "/operator/final-readiness" in paths
    assert "/operator/v1-finish-plan" in paths


def test_phase41_routes_do_not_expose_secrets() -> None:
    """Audit route paths do not expose secret names."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/audit") or route.path.startswith("/operator/v1") or route.path == "/operator/final-readiness")

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
