"""Operator route and safety tests."""

import importlib
import inspect

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app


def test_operator_routes_exist() -> None:
    """Operator routes are registered."""
    paths = {route.path for route in app.routes}

    assert "/operator/status" in paths
    assert "/operator/startup-checks" in paths
    assert "/operator/commands" in paths
    assert "/operator/daily-briefing" in paths
    assert "/operator/next-actions" in paths


def test_operator_routes_do_not_expose_secrets() -> None:
    """Operator route paths expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/operator"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths


def test_scripts_import_without_executing_real_trades() -> None:
    """Operator scripts import safely."""
    for module in ["scripts.operator_status", "scripts.operator_smoke_check", "scripts.operator_daily_briefing"]:
        imported = importlib.import_module(module)
        assert hasattr(imported, "main")


def test_no_kraken_add_order_added() -> None:
    """No Kraken AddOrder route surface exists."""
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
    """Routes expose no execution or fund movement surfaces."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
