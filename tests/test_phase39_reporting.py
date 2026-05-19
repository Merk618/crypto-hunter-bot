"""Phase 39 reporting tests."""

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


def test_reporting_includes_signal_quality_and_continuation_summary() -> None:
    """System health includes Phase 39 summaries."""
    report = UnifiedReportService(dashboard_service=Dashboard()).get_system_health_summary()

    assert "signal_quality_review" in report
    assert "observation_continuation_plan" in report
    assert report["observation_continuation_plan"]["paper_trades_allowed"] is False
    assert report["observation_continuation_plan"]["live_review_allowed"] is False
