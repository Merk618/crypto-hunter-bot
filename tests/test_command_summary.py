"""Command summary tests."""

from app.operator.command_summary import CommandSummaryBuilder


def test_command_summary_includes_pytest_command() -> None:
    """Pytest command is documented."""
    commands = " ".join(item["command"] for item in CommandSummaryBuilder().build().commands)

    assert "pytest" in commands


def test_command_summary_includes_uvicorn_command() -> None:
    """Backend start command is documented."""
    commands = " ".join(item["command"] for item in CommandSummaryBuilder().build().commands)

    assert "uvicorn app.main:app" in commands


def test_command_summary_includes_safety_audit_url() -> None:
    """Safety audit URL is documented."""
    commands = " ".join(item["command"] for item in CommandSummaryBuilder().build().commands)

    assert "/system/safety-audit" in commands
