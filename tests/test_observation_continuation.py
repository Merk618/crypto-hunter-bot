"""Observation continuation tests."""

from app.observation.observation_continuation import ObservationContinuationService


def quality(**updates):
    """Build quality report."""
    data = {
        "observations_analyzed": 20,
        "strong_buy_count": 1,
        "risk_approved_count": 1,
        "early_recovery_count": 0,
        "dominant_blockers": [],
    }
    data.update(updates)
    return data


def decision(**updates):
    """Build controlled paper decision report."""
    data = {"decision": "CONTINUE_OBSERVATION_ONLY"}
    data.update(updates)
    return data


def safety(**updates):
    """Build safety report."""
    data = {"passed": True, "live_trading_locked": True, "no_add_order_detected": True}
    data.update(updates)
    return data


def test_continuation_blocks_when_safety_audit_fails() -> None:
    """Safety failure blocks continuation."""
    plan = ObservationContinuationService().plan(quality_report=quality(), decision_report=decision(), safety_report=safety(passed=False))

    assert plan["decision"] == "BLOCKED"


def test_continuation_collects_more_when_sample_too_small() -> None:
    """Small sample requests more observations."""
    plan = ObservationContinuationService().plan(quality_report=quality(observations_analyzed=4), decision_report=decision(), safety_report=safety())

    assert plan["decision"] == "COLLECT_MORE_OBSERVATIONS"


def test_continuation_observe_only_when_no_strong_buy() -> None:
    """No STRONG_BUY stays observe-only."""
    plan = ObservationContinuationService().plan(quality_report=quality(strong_buy_count=0), decision_report=decision(), safety_report=safety())

    assert plan["decision"] == "CONTINUE_OBSERVATION_ONLY"


def test_continuation_observe_only_when_no_risk_approved() -> None:
    """No risk approval stays observe-only."""
    plan = ObservationContinuationService().plan(quality_report=quality(risk_approved_count=0), decision_report=decision(), safety_report=safety())

    assert plan["decision"] == "CONTINUE_OBSERVATION_ONLY"


def test_continuation_never_recommends_threshold_changes_paper_or_live() -> None:
    """Phase 39 keeps all execution/config actions disabled."""
    plan = ObservationContinuationService().plan(quality_report=quality(), decision_report=decision(decision="ELIGIBLE_FOR_CONFIG_REVIEW"), safety_report=safety())

    assert plan["threshold_changes_allowed"] is False
    assert plan["paper_trades_allowed"] is False
    assert plan["live_review_allowed"] is False
