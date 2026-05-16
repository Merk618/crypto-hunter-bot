"""Observation scheduler tests."""

from datetime import datetime, timedelta, timezone

from app.observation.observation_scheduler import ObservationScheduler


def test_minimum_seconds_between_runs_enforced() -> None:
    """Scheduler enforces minimum delay."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scheduler = ObservationScheduler(300, now_fn=lambda: now)

    assert scheduler.can_run_now() is True
    scheduler.record_run_started()
    scheduler.record_run_completed()
    assert scheduler.can_run_now() is False
    assert scheduler.seconds_until_next_run() == 300

    scheduler.now_fn = lambda: now + timedelta(seconds=301)
    assert scheduler.can_run_now() is True


def test_scheduler_status() -> None:
    """Scheduler status is structured."""
    scheduler = ObservationScheduler(300)

    status = scheduler.get_status()

    assert status["source"] == "crypto_hunter_observation_scheduler_v1"
