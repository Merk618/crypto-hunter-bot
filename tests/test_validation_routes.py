"""Validation route and safety tests."""

import inspect

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app


def test_validation_routes_exist() -> None:
    """Validation routes are registered."""
    paths = {route.path for route in app.routes}

    assert "/validation/status" in paths
    assert "/validation/run" in paths
    assert "/validation/kraken" in paths
    assert "/validation/moomoo" in paths
    assert "/validation/report" in paths


def test_validation_routes_do_not_expose_secrets() -> None:
    """Validation route paths expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/validation"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths


def test_no_kraken_add_order_added() -> None:
    """No Kraken AddOrder routes were added."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths


def test_no_moomoo_order_cancel_unlock_methods_added() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_no_options_execution_or_fund_movement_routes_added() -> None:
    """No execution or fund movement routes were added."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
