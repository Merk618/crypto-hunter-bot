"""Phase 36 controlled paper review route tests."""

from app.main import app


def test_phase36_review_audit_routes_exist() -> None:
    """Review/audit/guardrail routes exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/controlled-paper/review" in paths
    assert "/observation/controlled-paper/audit" in paths
    assert "/observation/controlled-paper/guardrails" in paths
    assert "/operator/controlled-paper-review" in paths


def test_phase36_routes_do_not_expose_secrets() -> None:
    """Controlled paper review routes expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if "controlled-paper" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
