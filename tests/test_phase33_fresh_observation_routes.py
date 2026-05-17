"""Phase 33 fresh observation route tests."""

from app.main import app


def test_phase33_fresh_observation_routes_exist() -> None:
    """Fresh validation routes exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/fresh-validation" in paths
    assert "/observation/fresh-validation/runs" in paths
    assert "/observation/fresh-validation/readiness" in paths
    assert "/operator/fresh-observation-check" in paths


def test_phase33_routes_do_not_expose_secrets() -> None:
    """Fresh validation routes do not expose secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if "fresh" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
