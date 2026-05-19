"""Local runbook tests."""

from app.operator.local_runbook import LocalOperatorRunbookService


def test_local_runbook_includes_required_commands() -> None:
    """Runbook includes expected operator commands."""
    report = LocalOperatorRunbookService().runbook()
    commands = " ".join(command["command"] for command in report["commands"])

    assert "pytest" in commands
    assert "uvicorn" in commands
    assert "health_check_phase42.py" in commands
    assert "controlled-paper/status" in commands


def test_startup_guide_includes_backend_start_and_stop() -> None:
    """Startup guide includes start and stop steps."""
    guide = LocalOperatorRunbookService().startup_guide()

    assert any("uvicorn" in step for step in guide["steps"])
    assert "Ctrl+C" in guide["stop_backend"]


def test_local_smoke_test_is_read_only() -> None:
    """Local smoke test returns read-only warnings."""
    report = LocalOperatorRunbookService().local_smoke_test()

    assert any("does not place trades" in warning for warning in report["warnings"])
