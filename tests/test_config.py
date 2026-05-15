"""Configuration safety tests."""

from app.config import BotMode, Settings


def test_default_mode_is_paper() -> None:
    """Default bot mode must be paper."""
    settings = Settings(_env_file=None)
    assert settings.bot_mode == BotMode.PAPER


def test_live_trading_disabled_by_default() -> None:
    """Live trading must be disabled by default."""
    settings = Settings(_env_file=None)
    assert settings.enable_live_trading is False
    assert settings.require_live_confirmation is True
    assert settings.live_trading_allowed() is False
