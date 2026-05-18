"""Phase 37 preflight route tests."""

from app.main import app


def test_phase37_preflight_routes_exist() -> None:
    """Preflight route paths exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/controlled-paper/preflight" in paths
    assert "/observation/controlled-paper/preflight/checks" in paths
    assert "/observation/controlled-paper/activation-plan" in paths
    assert "/observation/controlled-paper/preflight-package" in paths
    assert "/operator/controlled-paper-preflight" in paths


def test_phase37_routes_do_not_expose_secrets() -> None:
    """Preflight routes expose no secret names."""
    paths = " ".join(route.path.lower() for route in app.routes if "preflight" in route.path or "activation-plan" in route.path)

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths
