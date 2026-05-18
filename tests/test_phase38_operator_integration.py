"""Phase 38 operator integration tests."""

from app.operator.operator_service import OperatorService


class Decision:
    """Decision fake."""

    def decide(self):
        return {
            "decision": "CONTINUE_OBSERVATION_ONLY",
            "recommended_next_actions": ["Continue observation-only mode until repeated STRONG_BUY and risk-approved observations appear."],
        }


def test_operator_next_actions_include_decision_actions() -> None:
    """Operator next actions include decision guidance."""
    actions = OperatorService(controlled_decision=Decision()).get_next_recommended_actions()

    assert "Continue observation-only mode until repeated STRONG_BUY and risk-approved observations appear." in actions
