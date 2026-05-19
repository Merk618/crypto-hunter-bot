"""Phase 40 operator and reporting tests."""

from app.operator.operator_service import OperatorService
from app.reporting.unified_report_service import UnifiedReportService


class Checkpoint:
    """Checkpoint fake."""

    def checkpoint(self):
        return {"decision": "EXTEND_OBSERVATION_WINDOW", "recommended_next_actions": ["Run an extended persisted observation window before further review."]}


class Extended:
    """Extended plan fake."""

    def plan(self):
        return {"observe_only": True, "recommended_commands": ["Invoke-RestMethod /strategy/review-checkpoint"]}


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


def test_operator_next_actions_include_strategy_checkpoint() -> None:
    """Operator next actions include checkpoint guidance."""
    actions = OperatorService(strategy_checkpoint=Checkpoint(), extended_observation_plan=Extended()).get_next_recommended_actions()

    assert "Run an extended persisted observation window before further review." in actions


def test_reporting_includes_strategy_checkpoint_and_extended_plan() -> None:
    """System health includes Phase 40 summaries."""
    report = UnifiedReportService(dashboard_service=Dashboard()).get_system_health_summary()

    assert "strategy_review_checkpoint" in report
    assert "extended_observation_plan" in report
    assert report["extended_observation_plan"]["paper_trades_allowed"] is False
