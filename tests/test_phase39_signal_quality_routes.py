"""Phase 39 signal quality route tests."""

from app.main import app


def test_phase39_signal_quality_routes_exist() -> None:
    """Signal quality and continuation route paths exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/signal-quality" in paths
    assert "/observation/signal-quality/symbols" in paths
    assert "/observation/signal-quality/{symbol}" in paths
    assert "/observation/continuation-plan" in paths
    assert "/operator/signal-quality-review" in paths
    assert "/operator/observation-next-step" in paths


def test_phase39_routes_do_not_expose_secrets() -> None:
    """Route paths do not expose secret names."""
    paths = " ".join(route.path.lower() for route in app.routes if "signal-quality" in route.path or "continuation" in route.path or "observation-next-step" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
