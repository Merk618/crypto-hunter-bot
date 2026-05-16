"""MooMoo config tests."""

import pytest

from app.config import Settings
from app.connectors.moomoo.moomoo_config import get_moomoo_config


def test_moomoo_config_defaults_disabled_read_only() -> None:
    """MooMoo is disabled and read-only by default."""
    settings = Settings(_env_file=None)
    config = get_moomoo_config(settings)

    assert config.enabled is False
    assert config.read_only is True
    assert config.host == "127.0.0.1"
    assert config.port == 11111


def test_moomoo_trading_flags_default_false() -> None:
    """MooMoo trading flags remain locked by default."""
    settings = Settings(_env_file=None)
    config = get_moomoo_config(settings)

    assert config.trading_enabled is False
    assert config.paper_trading_enabled is False
    assert config.unlock_trade_context is False


def test_moomoo_unsafe_flags_are_rejected() -> None:
    """MooMoo trade-context flags fail config validation."""
    with pytest.raises(ValueError):
        Settings(_env_file=None, MOOMOO_TRADING_ENABLED=True)
    with pytest.raises(ValueError):
        Settings(_env_file=None, MOOMOO_UNLOCK_TRADE_CONTEXT=True)
