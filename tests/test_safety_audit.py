"""Safety audit tests."""

from pathlib import Path

from app.config import Settings
from app.core.safety_audit import SafetyAudit


def test_safety_audit_passes_under_default_safe_config() -> None:
    """Default configuration should pass the safety audit."""
    report = SafetyAudit(Settings(_env_file=None)).run()

    assert report.passed is True
    assert report.live_trading_locked is True
    assert report.no_add_order_detected is True
    assert report.no_withdrawal_methods_detected is True
    assert report.secrets_not_exposed is True


def test_safety_audit_flags_dangerous_live_trading_config() -> None:
    """Accidentally enabled live flags should fail the audit."""
    settings = Settings(_env_file=None, BOT_MODE="live", ENABLE_LIVE_TRADING=True, LIVE_TRADING_GATE_ENABLED=True)
    report = SafetyAudit(settings).run()

    assert report.passed is False
    assert report.dangerous_config_detected is True
    assert "dangerous live-trading configuration detected" in report.blockers


def test_safety_audit_detects_forbidden_live_order_strings_in_sample(tmp_path: Path) -> None:
    """The string scanner catches forbidden Kraken live-order calls in controlled input."""
    sample = tmp_path / "bad.py"
    sample.write_text("client.AddOrder({'pair': 'XBTUSD'})", encoding="utf-8")

    assert SafetyAudit().no_forbidden_live_order_strings([sample]) is False


def test_safety_audit_confirms_no_withdrawal_methods() -> None:
    """Exchange clients should expose no fund-movement methods."""
    assert SafetyAudit().no_forbidden_exchange_methods() is True
