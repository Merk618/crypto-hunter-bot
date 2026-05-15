"""Execution guard tests."""

import inspect

import pytest

from app.config import Settings
from app.execution.execution_guard import ExecutionGuard
from app.exchanges.kraken_private_client import KrakenPrivateClient


def test_execution_guard_blocks_live_orders_even_if_config_enabled() -> None:
    """Phase 12 never permits live execution."""
    settings = Settings(
        _env_file=None,
        BOT_MODE="live",
        ENABLE_LIVE_TRADING=True,
        LIVE_TRADING_GATE_ENABLED=True,
    )
    guard = ExecutionGuard(settings)

    assert guard.can_execute_live_order() is False
    with pytest.raises(RuntimeError, match="Live trading is locked"):
        guard.assert_live_trading_locked()


def test_execution_guard_blocks_private_trading_enabled() -> None:
    """Private Kraken trading remains blocked."""
    guard = ExecutionGuard(Settings(_env_file=None, KRAKEN_PRIVATE_TRADING_ENABLED=True))

    with pytest.raises(RuntimeError, match="private trading is disabled"):
        guard.assert_private_trading_disabled()


def test_execution_guard_safety_status_explains_locked_gates() -> None:
    """Safety status reports dry-run-only behavior."""
    status = ExecutionGuard(Settings(_env_file=None)).get_execution_safety_status()

    assert status["can_execute_live_order"] is False
    assert status["dry_run_execution_enabled"] is True
    assert "dry-run validation only" in status["locked_reason"]


def test_fastapi_execution_routes_exist() -> None:
    """Execution safety routes are registered."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/execution/safety-status" in paths
    assert "/execution/validate-order" in paths
    assert "/execution/dry-run-order" in paths
    assert "/execution/dry-runs" in paths
    assert "/execution/emergency-pause" in paths
    assert "/execution/emergency-stop" in paths
    assert "/execution/emergency-cancel-dry-run" in paths


def test_no_kraken_add_order_call_exists() -> None:
    """The private Kraken client has no order-placement method."""
    names = {name.lower() for name, _ in inspect.getmembers(KrakenPrivateClient)}
    assert "addorder" not in names
    assert "add_order" not in names
    assert "place_order" not in names


def test_no_withdrawal_methods_exist_on_private_client() -> None:
    """No withdrawal-style methods are exposed."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(KrakenPrivateClient))
    assert "withdraw" not in names
    assert "transfer" not in names
