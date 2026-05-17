"""Phase 34 operator/reporting integration tests."""

from app.operator.operator_service import OperatorService
from app.reporting.unified_report_service import UnifiedReportService


class Approval:
    """Approval fake."""

    def evaluate(self):
        return {
            "approval_status": "NOT_READY",
            "eligible_for_operator_review": False,
            "recommended_next_actions": ["Continue observation-only mode."],
        }


class Fresh:
    """Fresh fake."""

    def validate(self):
        return {"passed": False, "status": "INSUFFICIENT_DATA", "recommended_next_actions": ["Run a fresh observation window."]}


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


def test_operator_next_actions_include_approval_gate() -> None:
    """Operator next actions include approval-gate actions."""
    actions = OperatorService(fresh_validator=Fresh(), approval_gate=Approval()).get_next_recommended_actions()

    assert "Continue observation-only mode." in actions


def test_reporting_includes_paper_trade_approval_gate() -> None:
    """System health includes approval gate summary."""
    report = UnifiedReportService(dashboard_service=Dashboard()).get_system_health_summary()

    assert "paper_trade_approval_gate" in report
    assert report["paper_trade_approval_gate"]["paper_trade_observation_enabled"] is False
