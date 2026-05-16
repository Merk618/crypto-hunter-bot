"""Observation session manager tests."""

from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.observation.observation_session import ObservationSessionManager


class FakeEngine:
    """Fake paper observation engine."""

    def __init__(self):
        self.calls = []

    def run_once(self, manual_run=True, allow_paper_trades=False):
        self.calls.append({"manual_run": manual_run, "allow_paper_trades": allow_paper_trades})
        return {
            "status": "completed",
            "paper_trades_created": 1 if allow_paper_trades else 0,
            "results": [{"symbol": "BTC/USD", "signal": {"score": 54, "category": "NEUTRAL"}, "blockers": []}],
        }


def test_session_starts_with_target_run_count() -> None:
    """Session starts without auto-running."""
    engine = FakeEngine()
    manager = ObservationSessionManager(engine, settings=Settings())

    session = manager.start_session(target_runs=3)

    assert session["target_runs"] == 3
    assert engine.calls == []


def test_run_next_observation_calls_engine_and_increments_count() -> None:
    """Running next observation calls engine."""
    engine = FakeEngine()
    manager = ObservationSessionManager(engine, settings=Settings(observation_window_minutes_between_runs=0))
    manager.start_session(target_runs=2)

    response = manager.run_next_observation()

    assert len(engine.calls) == 1
    assert response["session"]["completed_runs"] == 1


def test_session_completes_when_target_runs_reached() -> None:
    """Session completes at target count."""
    manager = ObservationSessionManager(FakeEngine(), settings=Settings(observation_window_minutes_between_runs=0))
    manager.start_session(target_runs=1)

    response = manager.run_next_observation()

    assert response["session"]["status"] == "completed"


def test_paper_trades_disabled_by_default() -> None:
    """Paper trades are disabled by default."""
    engine = FakeEngine()
    manager = ObservationSessionManager(engine, settings=Settings(observation_window_minutes_between_runs=0))
    manager.start_session(target_runs=1, allow_paper_trades=True)
    manager.run_next_observation()

    assert engine.calls[0]["allow_paper_trades"] is False


def test_paper_trades_require_config_and_request_permission() -> None:
    """Paper trades require both config flags and explicit request."""
    engine = FakeEngine()
    settings = Settings(OBSERVATION_WINDOW_ALLOW_PAPER_TRADES=True, PAPER_OBSERVATION_ALLOW_PAPER_TRADES=True, OBSERVATION_WINDOW_MINUTES_BETWEEN_RUNS=0)
    manager = ObservationSessionManager(engine, settings=settings)
    manager.start_session(target_runs=1, allow_paper_trades=True)
    manager.run_next_observation()

    assert engine.calls[0]["allow_paper_trades"] is True


def test_minimum_interval_is_enforced() -> None:
    """Window interval prevents frequent runs unless ignored."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manager = ObservationSessionManager(FakeEngine(), settings=Settings(observation_window_minutes_between_runs=60), now_fn=lambda: now)
    manager.start_session(target_runs=2)
    manager.last_window_run_at = now - timedelta(minutes=10)

    response = manager.run_next_observation(ignore_interval=False)

    assert response["status"] == "refused"
    assert response["seconds_until_next_run"] > 0
