"""Phase 26 observation window route and safety tests."""

import inspect

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app


def test_observation_window_routes_exist() -> None:
    """Observation window routes exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/window/status" in paths
    assert "/observation/window/start" in paths
    assert "/observation/window/run-next" in paths
    assert "/observation/window/stop" in paths
    assert "/observation/window/summary" in paths
    assert "/observation/window/reset" in paths


def test_observation_window_routes_do_not_expose_secrets() -> None:
    """Observation window routes expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/observation/window"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths


def test_no_kraken_add_order_added_phase26() -> None:
    """No Kraken AddOrder route was added."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths


def test_no_moomoo_order_cancel_unlock_methods_added_phase26() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_no_options_execution_fund_movement_or_live_trading_added_phase26() -> None:
    """No options execution, fund movement, or live-trading routes exist."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
    assert "live-order" not in paths

