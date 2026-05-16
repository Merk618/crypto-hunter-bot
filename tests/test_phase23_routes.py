"""Phase 23 route and safety tests."""

import inspect

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app


def test_phase23_routes_exist() -> None:
    """Journal hygiene and observation routes exist."""
    paths = {route.path for route in app.routes}

    assert "/journal/hygiene/summary" in paths
    assert "/journal/hygiene/test-records" in paths
    assert "/journal/hygiene/production-preview" in paths
    assert "/observation/readiness" in paths


def test_phase23_routes_do_not_expose_secrets() -> None:
    """Route paths expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "api_key" not in paths
    assert "secret" not in paths


def test_no_kraken_add_order_added_phase23() -> None:
    """No Kraken AddOrder route was added."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths


def test_no_moomoo_order_cancel_unlock_methods_added_phase23() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_no_options_execution_or_fund_movement_added_phase23() -> None:
    """No options execution or fund movement routes exist."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
