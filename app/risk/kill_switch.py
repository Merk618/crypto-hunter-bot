"""Risk kill switch controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class KillSwitch:
    """Manual and API-failure-triggered kill switch."""

    max_api_failures_before_kill: int = 5
    active: bool = False
    reason: str | None = None
    activated_at: datetime | None = None
    deactivated_at: datetime | None = None
    api_failures: int = 0

    def activate(self, reason: str) -> None:
        """Activate the kill switch with a reason."""
        self.active = True
        self.reason = reason
        self.activated_at = datetime.now(timezone.utc)

    def deactivate(self, reason: str | None = None) -> None:
        """Deactivate the kill switch."""
        self.active = False
        self.reason = reason
        self.deactivated_at = datetime.now(timezone.utc)
        self.api_failures = 0

    def is_active(self) -> bool:
        """Return whether the kill switch is active."""
        return self.active

    def status(self) -> dict:
        """Return JSON-friendly kill switch status."""
        return {
            "active": self.active,
            "reason": self.reason,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
            "api_failures": self.api_failures,
            "max_api_failures_before_kill": self.max_api_failures_before_kill,
        }

    def record_api_failure(self) -> None:
        """Record an API failure and activate when threshold is reached."""
        self.api_failures += 1
        if self.api_failures >= self.max_api_failures_before_kill:
            self.activate("API failure threshold exceeded")

    def reset_api_failures(self) -> None:
        """Reset API failure count without changing active status."""
        self.api_failures = 0

    def update(self, daily_loss_fraction: float) -> bool:
        """Backward-compatible daily loss activation helper."""
        if daily_loss_fraction >= 0:
            self.activate("Daily loss limit exceeded")
        return self.active
