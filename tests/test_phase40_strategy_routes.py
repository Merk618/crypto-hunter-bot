"""Phase 40 strategy route tests."""

from app.main import app


def test_phase40_strategy_routes_exist() -> None:
    """Strategy review and operator routes exist."""
    paths = {route.path for route in app.routes}

    assert "/strategy/review-checkpoint" in paths
    assert "/strategy/extended-observation-plan" in paths
    assert "/strategy/review-package" in paths
    assert "/operator/strategy-review" in paths
    assert "/operator/extended-observation-next-step" in paths


def test_phase40_routes_do_not_expose_secrets() -> None:
    """Strategy route paths do not expose secret names."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/strategy") or "strategy-review" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
