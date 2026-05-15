"""Runtime bot state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class BotState:
    """State for the paper auto-trading bot."""

    is_running: bool = False
    is_paused: bool = False
    last_scan_at: datetime | None = None
    scans_completed: int = 0
    paper_trades_executed: int = 0
    last_error: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    mode: str = "paper"

    def start(self) -> None:
        """Mark the bot as running."""
        self.is_running = True
        self.is_paused = False
        self.started_at = datetime.now(timezone.utc)
        self.stopped_at = None
        self.last_error = None

    def stop(self) -> None:
        """Mark the bot as stopped."""
        self.is_running = False
        self.is_paused = False
        self.stopped_at = datetime.now(timezone.utc)

    def pause(self) -> None:
        """Pause the bot."""
        if self.is_running:
            self.is_paused = True

    def resume(self) -> None:
        """Resume the bot."""
        if self.is_running:
            self.is_paused = False

    def to_dict(self) -> dict:
        """Return JSON-friendly state."""
        data = asdict(self)
        for key in ["last_scan_at", "started_at", "stopped_at"]:
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data
