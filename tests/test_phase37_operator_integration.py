"""Phase 37 operator integration tests."""

from app.operator.operator_service import OperatorService


class Preflight:
    """Preflight fake."""

    def evaluate(self):
        return {"preflight_status": "OBSERVE_ONLY", "recommended_next_actions": ["Continue observation-only mode."]}


def test_operator_next_actions_include_preflight_actions() -> None:
    """Operator next actions include preflight recommendations."""
    actions = OperatorService(controlled_preflight=Preflight()).get_next_recommended_actions()

    assert "Continue observation-only mode." in actions
