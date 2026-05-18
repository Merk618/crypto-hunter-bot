"""Phase 37 reporting tests."""

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


def test_reporting_includes_preflight_summary() -> None:
    """System health includes controlled paper preflight."""
    report = UnifiedReportService(dashboard_service=Dashboard()).get_system_health_summary()

    assert "controlled_paper_preflight" in report
    assert "activation_eligible" in report["controlled_paper_preflight"]
