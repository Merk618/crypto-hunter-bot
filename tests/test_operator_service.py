"""Operator service tests."""

from app.config import Settings
from app.operator.operator_service import OperatorService


def test_operator_service_returns_status_with_safe_defaults() -> None:
    """Operator status is available with defaults."""
    status = OperatorService(settings=Settings(_env_file=None)).get_operator_status()

    assert status["mode"] == "paper"
    assert status["backend_healthy"] is True
    assert status["paper_status"]["safe"] is True


def test_operator_service_confirms_live_trading_locked() -> None:
    """Live trading remains locked."""
    status = OperatorService(settings=Settings(_env_file=None)).get_operator_status()

    assert status["live_trading_locked"] is True


def test_operator_daily_briefing_handles_missing_data() -> None:
    """Daily briefing returns structure even with unavailable optional data."""
    briefing = OperatorService(settings=Settings(_env_file=None)).get_daily_operator_briefing()

    assert "daily_briefing" in briefing
    assert "next_actions" in briefing


def test_operator_next_actions_are_returned() -> None:
    """Next actions are returned."""
    actions = OperatorService(settings=Settings(_env_file=None)).get_next_recommended_actions()

    assert actions
