"""Cooldown manager tests."""

from datetime import datetime, timedelta, timezone

from app.risk.cooldown_manager import CooldownManager


class Clock:
    """Mutable test clock."""

    def __init__(self) -> None:
        """Initialize clock."""
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def advance(self, minutes: int) -> None:
        """Advance clock."""
        self.now += timedelta(minutes=minutes)


def test_cooldown_manager_sets_and_clears_cooldown() -> None:
    """Cooldown can be set and cleared."""
    clock = Clock()
    manager = CooldownManager(now_fn=lambda: clock.now)
    manager.set_symbol_cooldown("BTC/USD", 10, "test")
    assert manager.is_symbol_on_cooldown("BTC-USD") is True
    manager.clear_symbol_cooldown("BTC/USD")
    assert manager.is_symbol_on_cooldown("BTC/USD") is False


def test_cooldown_manager_records_trade_cooldown() -> None:
    """Trade cooldown uses configured minutes."""
    clock = Clock()
    manager = CooldownManager(after_trade_minutes=15, now_fn=lambda: clock.now)
    manager.record_trade("BTC/USD")
    assert manager.is_symbol_on_cooldown("BTC/USD") is True
    clock.advance(16)
    assert manager.is_symbol_on_cooldown("BTC/USD") is False


def test_cooldown_manager_records_loss_cooldown() -> None:
    """Loss cooldown uses configured minutes."""
    clock = Clock()
    manager = CooldownManager(after_loss_minutes=60, now_fn=lambda: clock.now)
    manager.record_loss("BTC/USD")
    assert manager.is_symbol_on_cooldown("BTC/USD") is True
    clock.advance(30)
    assert manager.is_symbol_on_cooldown("BTC/USD") is True
    clock.advance(31)
    assert manager.is_symbol_on_cooldown("BTC/USD") is False
