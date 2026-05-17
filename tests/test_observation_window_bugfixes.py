"""Phase 27 observation window bugfix tests."""

from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.observation.observation_session import ObservationSessionManager
from app.observation.observation_window import build_observation_window_summary


class FakeEngine:
    """Fake engine with configurable run status."""

    def __init__(self, status="completed"):
        self.status = status
        self.calls = []
        self.scheduler = type("Scheduler", (), {"last_run_started_at": datetime(2026, 1, 1, tzinfo=timezone.utc), "is_running": False})()

    def run_once(self, manual_run=True, allow_paper_trades=False):
        self.calls.append({"manual_run": manual_run, "allow_paper_trades": allow_paper_trades})
        return {"status": self.status, "paper_trades_created": 0, "results": [{"symbol": "BTC/USD", "signal": {"score": 54, "category": "NEUTRAL"}}] if self.status == "completed" else []}


def test_refused_runs_do_not_increment_completed_runs() -> None:
    """Refused lower-level runs are not counted as completed."""
    manager = ObservationSessionManager(FakeEngine(status="refused"), settings=Settings(OBSERVATION_WINDOW_MINUTES_BETWEEN_RUNS=0))
    manager.start_session(target_runs=2)

    response = manager.run_next_observation()

    assert response["session"]["completed_runs"] == 0
    assert response["session"]["refused_runs"] == 1


def test_completed_runs_increment_completed_runs() -> None:
    """Completed runs increment completed count."""
    manager = ObservationSessionManager(FakeEngine(status="completed"), settings=Settings(OBSERVATION_WINDOW_MINUTES_BETWEEN_RUNS=0))
    manager.start_session(target_runs=2)

    response = manager.run_next_observation()

    assert response["session"]["completed_runs"] == 1
    assert response["session"]["refused_runs"] == 0


def test_summary_counts_only_completed_runs_as_runs_analyzed() -> None:
    """Summary excludes refused runs from analyzed run count."""
    runs = [
        {"status": "completed", "results": [{"symbol": "BTC/USD", "signal": {"score": 54, "category": "NEUTRAL"}}]},
        {"status": "refused", "results": []},
    ]

    summary = build_observation_window_summary("session", runs).to_dict()

    assert summary["runs_analyzed"] == 1
    assert summary["completed_runs_analyzed"] == 1
    assert summary["refused_runs_count"] == 1
    assert summary["total_attempted_runs"] == 2


def test_ignore_interval_bypasses_lower_scheduler_when_requested() -> None:
    """Explicit interval ignore clears lower scheduler throttle before run."""
    engine = FakeEngine(status="completed")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manager = ObservationSessionManager(engine, settings=Settings(OBSERVATION_WINDOW_MINUTES_BETWEEN_RUNS=60), now_fn=lambda: now)
    manager.start_session(target_runs=1)
    manager.last_window_run_at = now - timedelta(minutes=10)

    response = manager.run_next_observation(ignore_interval=True)

    assert response["session"]["completed_runs"] == 1
    assert engine.scheduler.last_run_started_at is None

