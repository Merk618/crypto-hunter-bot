"""Phase 33 reporting tests."""

from app.reporting.unified_report_service import UnifiedReportService


class Dashboard:
    """Dashboard fake."""

    def get_risk_summary(self):
        return Obj({})

    def get_overview(self):
        return Obj({})

    def get_signal_performance(self, limit=100):
        return Obj({"recent_signals": []})


class Obj:
    """to_dict fake."""

    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data


def test_reporting_includes_fresh_validation_summary() -> None:
    """System health includes fresh validation."""
    report = UnifiedReportService(dashboard_service=Dashboard()).get_system_health_summary()

    assert "fresh_observation_validation" in report
    assert "clean_observation_verification" in report
    assert "legacy_aware_risk_readiness" in report


def test_daily_briefing_handles_fresh_validation() -> None:
    """Daily briefing includes system health with fresh validation."""
    briefing = UnifiedReportService(dashboard_service=Dashboard()).get_daily_briefing()

    assert "system_health" in briefing
    assert "fresh_observation_validation" in briefing["system_health"]
