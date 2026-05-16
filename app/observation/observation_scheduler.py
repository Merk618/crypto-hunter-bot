"""Simple observation run throttle state."""

from __future__ import annotations

from datetime import datetime, timezone


class ObservationScheduler:
    """Track manual observation run timing."""

    def __init__(self, min_seconds_between_runs: int = 300, now_fn=None) -> None:
        """Initialize scheduler state."""
        self.min_seconds_between_runs = min_seconds_between_runs
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.last_run_started_at: datetime | None = None
        self.last_run_completed_at: datetime | None = None
        self.is_running = False

    def can_run_now(self) -> bool:
        """Return True if throttle permits a run."""
        return self.seconds_until_next_run() == 0 and not self.is_running

    def record_run_started(self) -> None:
        """Mark run start."""
        self.is_running = True
        self.last_run_started_at = self.now_fn()

    def record_run_completed(self) -> None:
        """Mark run completion."""
        self.is_running = False
        self.last_run_completed_at = self.now_fn()

    def seconds_until_next_run(self) -> int:
        """Return seconds until another run is allowed."""
        if self.last_run_started_at is None:
            return 0
        elapsed = (self.now_fn() - self.last_run_started_at).total_seconds()
        return max(0, int(self.min_seconds_between_runs - elapsed))

    def get_status(self) -> dict:
        """Return scheduler status."""
        return {
            "is_running": self.is_running,
            "can_run_now": self.can_run_now(),
            "seconds_until_next_run": self.seconds_until_next_run(),
            "last_run_started_at": self.last_run_started_at.isoformat() if self.last_run_started_at else None,
            "last_run_completed_at": self.last_run_completed_at.isoformat() if self.last_run_completed_at else None,
            "source": "crypto_hunter_observation_scheduler_v1",
        }
