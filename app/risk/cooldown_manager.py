"""Symbol cooldown management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class CooldownManager:
    """Track timestamp-based symbol cooldowns."""

    def __init__(self, after_trade_minutes: int = 15, after_loss_minutes: int = 60, now_fn=None) -> None:
        """Initialize cooldown settings."""
        self.after_trade_minutes = after_trade_minutes
        self.after_loss_minutes = after_loss_minutes
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._cooldowns: dict[str, dict] = {}

    def set_symbol_cooldown(self, symbol: str, minutes: int, reason: str) -> None:
        """Set a cooldown for a symbol."""
        normalized = self._normalize_symbol(symbol)
        self._cooldowns[normalized] = {
            "symbol": normalized,
            "reason": reason,
            "expires_at": self._now_fn() + timedelta(minutes=minutes),
        }

    def is_symbol_on_cooldown(self, symbol: str) -> bool:
        """Return whether a symbol is currently on cooldown."""
        cooldown = self.get_symbol_cooldown(symbol)
        return bool(cooldown and cooldown["active"])

    def get_symbol_cooldown(self, symbol: str) -> dict | None:
        """Return cooldown details for a symbol."""
        normalized = self._normalize_symbol(symbol)
        cooldown = self._cooldowns.get(normalized)
        if not cooldown:
            return None
        active = self._now_fn() < cooldown["expires_at"]
        return {
            "symbol": normalized,
            "reason": cooldown["reason"],
            "expires_at": cooldown["expires_at"].isoformat(),
            "active": active,
        }

    def clear_symbol_cooldown(self, symbol: str) -> None:
        """Clear a symbol cooldown."""
        self._cooldowns.pop(self._normalize_symbol(symbol), None)

    def record_trade(self, symbol: str) -> None:
        """Record a trade cooldown."""
        self.set_symbol_cooldown(symbol, self.after_trade_minutes, "trade cooldown")

    def record_loss(self, symbol: str) -> None:
        """Record a longer loss cooldown."""
        self.set_symbol_cooldown(symbol, self.after_loss_minutes, "loss cooldown")

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbols."""
        return symbol.strip().upper().replace("-", "/")
