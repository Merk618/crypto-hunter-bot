"""Startup checks tests."""

from pathlib import Path

from app.config import Settings
from app.operator.startup_checks import StartupChecks


def test_startup_checks_pass_under_safe_default_config() -> None:
    """Safe defaults pass startup checks."""
    result = StartupChecks(settings=Settings(_env_file=None)).run()

    assert result.passed is True
    assert result.checks["live_trading_locked"] is True
    assert result.checks["env_example_safe_defaults"] is True


def test_startup_checks_flag_dangerous_config_in_mocked_setting(tmp_path: Path) -> None:
    """A fake unsafe setting is flagged without needing invalid Settings."""
    checks = StartupChecks(settings=Settings(_env_file=None))
    checks.settings.enable_live_trading = True

    result = checks.run()

    assert result.passed is False
    assert "live trading is not locked" in result.blockers
