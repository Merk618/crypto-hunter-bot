"""Phase 39 operator integration tests."""

from app.operator.operator_service import OperatorService


class Quality:
    """Signal quality fake."""

    def review(self):
        return {"strong_buy_count": 0, "recommended_next_actions": ["Keep thresholds unchanged."]}


class Continuation:
    """Continuation fake."""

    def plan(self):
        return {"decision": "CONTINUE_OBSERVATION_ONLY", "recommended_next_actions": ["Continue persisted observation windows."]}


def test_operator_next_actions_include_signal_quality_and_continuation() -> None:
    """Operator next actions include Phase 39 guidance."""
    actions = OperatorService(signal_quality=Quality(), observation_continuation=Continuation()).get_next_recommended_actions()

    assert "Keep thresholds unchanged." in actions
    assert "Continue persisted observation windows." in actions
