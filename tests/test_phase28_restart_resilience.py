"""Phase 28 restart resilience and route tests."""

import inspect

from app.calibration.strategy_decision_gate import StrategyDecisionGate
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app


def test_empty_persisted_history_returns_keep_observing() -> None:
    """Empty hydrated history is clean."""
    report = StrategyDecisionGate().evaluate([]).to_dict()

    assert report["decision"] == "KEEP_OBSERVING"
    assert report["observations_analyzed"] == 0
    assert report["live_review_allowed"] is False


def test_observation_history_routes_exist() -> None:
    """History routes exist."""
    paths = {route.path for route in app.routes}

    assert "/observation/history" in paths
    assert "/observation/history/runs" in paths
    assert "/observation/history/results" in paths
    assert "/observation/history/summary" in paths


def test_observation_history_routes_do_not_expose_secrets() -> None:
    """History routes expose no secrets."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/observation/history"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths


def test_no_kraken_add_order_added_phase28() -> None:
    """No Kraken AddOrder route was added."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths


def test_no_moomoo_order_cancel_unlock_methods_added_phase28() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_no_options_execution_fund_movement_or_live_trading_added_phase28() -> None:
    """No options execution, fund movement, or live-trading routes exist."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
    assert "live-order" not in paths

