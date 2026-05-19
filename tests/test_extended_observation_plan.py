"""Extended observation plan tests."""

from app.observation.extended_observation_plan import ExtendedObservationPlanService


def checkpoint(**updates):
    """Build checkpoint summary."""
    data = {
        "decision": "CONTINUE_OBSERVATION_ONLY",
        "strong_buy_count": 0,
        "risk_approved_count": 0,
        "early_recovery_count": 1,
        "dominant_blockers": [{"text": "close at or below EMA 200", "count": 10}],
        "strongest_symbols": [{"symbol": "SUI/USD"}],
    }
    data.update(updates)
    return data


def test_extended_plan_is_observe_only() -> None:
    """Plan is observe-only."""
    plan = ExtendedObservationPlanService().plan(checkpoint())

    assert plan["observe_only"] is True
    assert plan["threshold_changes_allowed"] is False


def test_extended_plan_disallows_paper_and_live() -> None:
    """Plan disallows paper/live review."""
    plan = ExtendedObservationPlanService().plan(checkpoint())

    assert plan["paper_trades_allowed"] is False
    assert plan["live_review_allowed"] is False


def test_extended_plan_includes_recommended_commands() -> None:
    """Plan includes operator commands."""
    plan = ExtendedObservationPlanService().plan(checkpoint())

    assert plan["recommended_commands"]
    assert any("strategy/review-checkpoint" in command for command in plan["recommended_commands"])
