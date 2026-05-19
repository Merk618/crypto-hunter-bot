"""Phase 41 operator and reporting tests."""

from app.operator.operator_service import OperatorService
from app.reporting.unified_report_service import UnifiedReportService


class Readiness:
    """Readiness fake."""

    def audit(self):
        return {"readiness_status": "READY_FOR_FINAL_RUNBOOK", "recommended_next_actions": ["Phase 42: create local operator runbook and one-command health check."]}


class Checklist:
    """Checklist fake."""

    def build(self):
        return {"recommended_finish_steps": ["Phase 43: prepare v1 freeze and handoff package."]}


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


def test_operator_next_actions_include_final_readiness() -> None:
    """Operator next actions include final finish guidance."""
    actions = OperatorService(standalone_readiness=Readiness(), v1_checklist=Checklist()).get_next_recommended_actions()

    assert "Phase 42: create local operator runbook and one-command health check." in actions
    assert "Phase 43: prepare v1 freeze and handoff package." in actions


def test_reporting_includes_standalone_readiness() -> None:
    """System health includes Phase 41 summaries."""
    report = UnifiedReportService(dashboard_service=Dashboard()).get_system_health_summary()

    assert "standalone_readiness" in report
    assert "final_safety_review" in report
    assert "v1_completion_checklist" in report
