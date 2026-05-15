"""Execution safety guard."""

from __future__ import annotations

from app.config import Settings, get_settings


class ExecutionGuard:
    """Ensure live execution remains impossible in this phase."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize guard."""
        self.settings = settings or get_settings()

    def assert_live_trading_locked(self) -> None:
        """Raise if live trading appears enabled."""
        if self.settings.live_trading_gate_enabled or self.settings.enable_live_trading:
            raise RuntimeError("Live trading is locked in Phase 12")

    def assert_no_withdrawal_methods(self) -> bool:
        """Return True because no withdrawal methods are implemented."""
        return True

    def assert_private_trading_disabled(self) -> None:
        """Raise if private trading config is enabled."""
        if self.settings.kraken_private_trading_enabled:
            raise RuntimeError("Kraken private trading is disabled in Phase 12")

    def can_execute_live_order(self) -> bool:
        """Live execution is always false in Phase 12."""
        return False

    def get_execution_safety_status(self) -> dict:
        """Return safety gate status."""
        return {
            "can_execute_live_order": False,
            "live_trading_gate_enabled": self.settings.live_trading_gate_enabled,
            "enable_live_trading": self.settings.enable_live_trading,
            "dry_run_execution_enabled": self.settings.dry_run_execution_enabled,
            "kraken_private_trading_enabled": self.settings.kraken_private_trading_enabled,
            "emergency_cancel_enabled": self.settings.emergency_cancel_enabled,
            "dead_man_switch_enabled": self.settings.dead_man_switch_enabled,
            "locked_reason": "Phase 12 supports dry-run validation only",
        }
