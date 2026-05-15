"""Kill switch tests."""

from app.risk.kill_switch import KillSwitch


def test_kill_switch_activates_and_deactivates_correctly() -> None:
    """KillSwitch can be manually toggled."""
    kill = KillSwitch(max_api_failures_before_kill=3)
    kill.activate("manual test")
    assert kill.is_active() is True
    assert kill.status()["reason"] == "manual test"
    kill.deactivate("resume")
    assert kill.is_active() is False


def test_kill_switch_activates_after_repeated_api_failures() -> None:
    """Repeated API failures activate the kill switch."""
    kill = KillSwitch(max_api_failures_before_kill=2)
    kill.record_api_failure()
    assert kill.is_active() is False
    kill.record_api_failure()
    assert kill.is_active() is True
    assert kill.status()["api_failures"] == 2
