"""Observation session state models and manager."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from app.config import Settings, get_settings
from app.observation.observation_metrics import calculate_calibration_readiness


@dataclass
class ObservationSession:
    """Longer paper observation session state."""

    session_id: str
    started_at: str
    completed_at: str | None
    status: str
    target_runs: int
    completed_runs: int
    symbols: list[str]
    timeframe: str
    allow_paper_trades: bool = False
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    source: str = "crypto_hunter_observation_session_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class ObservationSessionManager:
    """Manage a manual paper observation window without background loops."""

    def __init__(self, observation_engine, settings: Settings | None = None, now_fn=None) -> None:
        """Initialize manager."""
        self.settings = settings or get_settings()
        self.observation_engine = observation_engine
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.session: ObservationSession | None = None
        self.session_runs: list[dict] = []
        self.last_window_run_at: datetime | None = None

    def start_session(self, target_runs: int | None = None, allow_paper_trades: bool = False) -> dict:
        """Start a manual session without running observations."""
        allowed_paper = bool(allow_paper_trades and self.settings.observation_window_allow_paper_trades and self.settings.paper_observation_allow_paper_trades)
        warnings = []
        if allow_paper_trades and not allowed_paper:
            warnings.append("Paper trades requested but disabled by observation window and paper observation settings.")
        self.session = ObservationSession(
            session_id=str(uuid.uuid4()),
            started_at=self.now_fn().isoformat(),
            completed_at=None,
            status="running",
            target_runs=target_runs or self.settings.observation_window_default_runs,
            completed_runs=0,
            symbols=self.settings.observation_window_symbols,
            timeframe=self.settings.observation_window_timeframe,
            allow_paper_trades=allowed_paper,
            warnings=warnings,
        )
        self.session_runs = []
        self.last_window_run_at = None
        return self.session.to_dict()

    def stop_session(self) -> dict:
        """Stop the current session."""
        if self.session is None:
            return {"status": "stopped", "message": "no active observation session", "source": "crypto_hunter_observation_session_status_v1"}
        self.session.status = "stopped"
        self.session.completed_at = self.now_fn().isoformat()
        return self.session.to_dict()

    def get_session_status(self) -> dict:
        """Return current session status."""
        return {
            "enabled": self.settings.observation_window_enabled,
            "read_only": self.settings.observation_window_read_only,
            "paper_trades_allowed_by_config": self.settings.observation_window_allow_paper_trades,
            "session": self.session.to_dict() if self.session else None,
            "runs_collected": len(self.session_runs),
            "seconds_until_next_run": self._seconds_until_next_run(),
            "calibration_readiness": calculate_calibration_readiness(len(self.session_runs), self.settings.observation_window_min_runs_for_summary),
            "source": "crypto_hunter_observation_window_status_v1",
        }

    def run_next_observation(self, manual_run: bool = True, ignore_interval: bool = False) -> dict:
        """Run the next manual observation in the current session."""
        if self.session is None:
            self.start_session()
        if self.session and self.session.status == "completed":
            return {"status": "refused", "blockers": ["observation session already completed"], "source": "crypto_hunter_observation_window_run_v1"}
        if not ignore_interval and self._seconds_until_next_run() > 0:
            return {"status": "refused", "blockers": ["observation window interval has not elapsed"], "seconds_until_next_run": self._seconds_until_next_run(), "source": "crypto_hunter_observation_window_run_v1"}
        allow_paper = bool(self.session and self.session.allow_paper_trades)
        run = self.observation_engine.run_once(manual_run=manual_run, allow_paper_trades=allow_paper)
        self.last_window_run_at = self.now_fn()
        self.session_runs.insert(0, run)
        if self.session:
            self.session.completed_runs = len(self.session_runs)
            if self.session.completed_runs >= self.session.target_runs:
                self.session.status = "completed"
                self.session.completed_at = self.now_fn().isoformat()
        return {"session": self.session.to_dict() if self.session else None, "run": run, "source": "crypto_hunter_observation_window_run_v1"}

    def get_window_summary(self) -> dict:
        """Return current session summary."""
        from app.observation.observation_window import build_observation_window_summary

        session_id = self.session.session_id if self.session else "no-session"
        return build_observation_window_summary(session_id, self.session_runs, self.settings).to_dict()

    def reset_session(self) -> dict:
        """Reset current observation session state."""
        self.session = None
        self.session_runs = []
        self.last_window_run_at = None
        return {"status": "reset", "source": "crypto_hunter_observation_window_reset_v1"}

    def _seconds_until_next_run(self) -> int:
        """Return seconds until next window run is allowed."""
        if self.last_window_run_at is None:
            return 0
        interval = timedelta(minutes=self.settings.observation_window_minutes_between_runs)
        elapsed = self.now_fn() - self.last_window_run_at
        return max(0, int((interval - elapsed).total_seconds()))

