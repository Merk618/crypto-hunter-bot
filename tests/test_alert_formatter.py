"""Alert formatter tests."""

from app.alerts.alert_formatter import AlertFormatter
from app.alerts.alert_models import AlertCandidate, AlertReport


def report() -> AlertReport:
    """Create report with all sections."""
    crypto = AlertCandidate("crypto", "BTC/USD", "BTC signal", 88, "STRONG_BUY").to_dict()
    stock = AlertCandidate("stock", "AAPL", "AAPL stock", 82, "LEADING").to_dict()
    option = AlertCandidate("option", "AAPL260619C00150000", "AAPL call", 79, "RESEARCH_CANDIDATE").to_dict()
    return AlertReport("Test Alert", [crypto], [stock], [option], {"kill_switch_active": False}, {"passed": True})


def test_alert_formatter_creates_markdown_report() -> None:
    """Markdown report is created."""
    output = AlertFormatter().format_markdown_report(report())

    assert output.startswith("# Test Alert")


def test_alert_formatter_includes_crypto_stock_options_sections() -> None:
    """All candidate sections appear."""
    output = AlertFormatter().format_markdown_report(report())

    assert "Top Crypto Candidates" in output
    assert "Top Stock Candidates" in output
    assert "Top Options Candidates" in output
