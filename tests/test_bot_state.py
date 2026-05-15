"""Bot state tests."""

from app.bot.bot_state import BotState


def test_bot_starts_stopped() -> None:
    """BotState starts stopped."""
    state = BotState()
    assert state.is_running is False
    assert state.is_paused is False
    assert state.mode == "paper"


def test_bot_state_lifecycle() -> None:
    """BotState supports start, pause, resume, and stop."""
    state = BotState()
    state.start()
    assert state.is_running is True
    state.pause()
    assert state.is_paused is True
    state.resume()
    assert state.is_paused is False
    state.stop()
    assert state.is_running is False
