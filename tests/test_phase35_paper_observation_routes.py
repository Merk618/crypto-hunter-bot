"""Phase 35 controlled paper route tests."""

from app.main import app


def test_phase35_controlled_paper_routes_exist() -> None:
    """Controlled paper routes exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/controlled-paper/status" in paths
    assert "/observation/controlled-paper/evaluate" in paths
    assert "/observation/controlled-paper/preview" in paths
    assert "/observation/controlled-paper/run-once" in paths
    assert "/observation/controlled-paper/recent" in paths
    assert "/operator/controlled-paper-observation" in paths


def test_phase35_routes_do_not_expose_secrets() -> None:
    """Controlled paper routes expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if "controlled-paper" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
