"""Phase 35 operator/reporting integration tests."""

from app.operator.operator_service import OperatorService
from app.reporting.unified_report_service import UnifiedReportService


class Controlled:
    """Controlled paper fake."""

    def status(self):
        return {"enabled": False, "paper_trade_observation_enabled": False}

    def evaluate(self):
        return {"status": "DISABLED_BY_CONFIG"}


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


def test_operator_next_actions_include_controlled_paper_status() -> None:
    """Operator next actions include controlled paper disabled message."""
    actions = OperatorService(controlled_paper=Controlled()).get_next_recommended_actions()

    assert "Controlled paper observation is disabled by config." in actions


def test_reporting_includes_controlled_paper_observation_state() -> None:
    """System health includes controlled paper status."""
    report = UnifiedReportService(dashboard_service=Dashboard()).get_system_health_summary()

    assert "controlled_paper_observation" in report
    assert report["controlled_paper_observation"]["enabled"] is False
