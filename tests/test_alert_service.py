"""Alert service tests."""

from app.alerts.alert_service import AlertService
from app.config import Settings


class FakeUnifiedReportService:
    """Fake report service."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def get_top_candidates(self) -> dict:
        """Return fake candidates."""
        if self.fail:
            raise RuntimeError("missing data")
        return {
            "crypto": [{"asset_class": "crypto", "symbol": "BTC/USD", "title": "BTC", "score": 90, "category": "STRONG_BUY", "reasons": [], "warnings": [], "blockers": [], "metadata": {}, "source": "test"}],
            "stocks": [],
            "options": [],
        }

    def get_system_health_summary(self) -> dict:
        """Return fake health."""
        if self.fail:
            raise RuntimeError("missing health")
        return {"risk": {"kill_switch_active": False}, "safety": {"passed": True}}


def test_alert_service_preview_works_when_alerts_disabled() -> None:
    """Preview works even when sending is disabled."""
    service = AlertService(settings=Settings(_env_file=None), unified_report_service=FakeUnifiedReportService())

    preview = service.preview_alert_report()

    assert preview["report"]["crypto_candidates"]
    assert "markdown" in preview


def test_alert_service_blocks_real_sending_when_alerts_disabled() -> None:
    """Console sending is blocked when alerts disabled."""
    service = AlertService(settings=Settings(_env_file=None), unified_report_service=FakeUnifiedReportService())

    result = service.send_console_alert()

    assert result["attempted"] is False
    assert result["sent"] is False


def test_discord_dry_run_does_not_call_external_webhook() -> None:
    """Discord endpoint is dry-run only."""
    service = AlertService(settings=Settings(_env_file=None, DISCORD_WEBHOOK_URL="https://example.invalid/hook"), unified_report_service=FakeUnifiedReportService())

    result = service.send_discord_alert_dry_run()

    assert result["attempted"] is False
    assert result["sent"] is False
    assert "example.invalid" not in result["message"]


def test_alert_service_handles_missing_data_gracefully() -> None:
    """Missing data becomes a warning, not a crash."""
    service = AlertService(settings=Settings(_env_file=None), unified_report_service=FakeUnifiedReportService(fail=True))

    preview = service.preview_alert_report()

    assert preview["report"]["warnings"]
