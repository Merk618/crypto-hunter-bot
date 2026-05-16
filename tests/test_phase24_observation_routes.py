"""Phase 24 observation route and safety tests."""

import inspect

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app


def test_observation_status_route_exists() -> None:
    """Observation status route exists."""
    assert "/observation/status" in {route.path for route in app.routes}


def test_observation_run_once_route_exists() -> None:
    """Observation run route exists."""
    assert "/observation/run-once" in {route.path for route in app.routes}


def test_observation_recent_route_exists() -> None:
    """Observation recent route exists."""
    assert "/observation/recent" in {route.path for route in app.routes}


def test_observation_report_route_exists() -> None:
    """Observation report route exists."""
    assert "/observation/report" in {route.path for route in app.routes}


def test_observation_routes_do_not_expose_secrets() -> None:
    """Observation routes expose no secret paths."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/observation"))

    assert "secret" not in paths
    assert "api_key" not in paths


def test_no_kraken_add_order_added_phase24() -> None:
    """No Kraken AddOrder route was added."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths


def test_no_moomoo_order_cancel_unlock_methods_added_phase24() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_no_options_execution_or_fund_movement_added_phase24() -> None:
    """No options execution or fund movement routes exist."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
