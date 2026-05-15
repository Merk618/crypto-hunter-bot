"""Emergency control tests."""

from app.bot.bot_state import BotState
from app.config import Settings
from app.execution.emergency_controls import EmergencyControls


def test_emergency_controls_can_pause_bot_state() -> None:
    """Emergency pause marks a running bot as paused."""
    state = BotState()
    state.start()
    result = EmergencyControls(bot_state=state, settings=Settings(_env_file=None)).emergency_pause_bot("test pause")

    assert result["status"] == "paused"
    assert state.is_paused is True


def test_emergency_controls_can_stop_bot_state() -> None:
    """Emergency stop marks the bot as stopped."""
    state = BotState()
    state.start()
    result = EmergencyControls(bot_state=state, settings=Settings(_env_file=None)).emergency_stop_bot("test stop")

    assert result["status"] == "stopped"
    assert state.is_running is False


def test_emergency_live_cancel_is_dry_run_only() -> None:
    """Emergency cancel never calls a live exchange in Phase 12."""
    result = EmergencyControls(settings=Settings(_env_file=None)).emergency_cancel_live_orders_dry_run("test cancel")

    assert result["status"] == "DRY_RUN"
    assert "No live cancel endpoint called" in result["message"]


def test_dead_man_switch_status_is_safe_by_default() -> None:
    """Dead-man switch reports disabled with no live actions."""
    status = EmergencyControls(settings=Settings(_env_file=None)).dead_man_switch_status()

    assert status["enabled"] is False
    assert status["live_actions_enabled"] is False
