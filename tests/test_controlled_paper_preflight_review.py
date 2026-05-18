"""Controlled paper preflight review decision tests."""

from app.config import Settings
from app.observation.controlled_paper_preflight_review import ControlledPaperPreflightReviewService


def settings(**updates):
    """Build settings overrides."""
    return Settings(_env_file=None).model_copy(update=updates)


def result(category="STRONG_BUY", approved=True):
    """Build observation result."""
    return {"signal": {"category": category}, "risk_decision": {"approved": approved}}


def runs(category="STRONG_BUY", approved=True, count=5):
    """Build completed observation runs."""
    return [{"status": "completed", "results": [result(category, approved) for _ in range(4)]} for _ in range(count)]


def summaries(**overrides):
    """Build clean decision summaries."""
    data = {
        "safety": {"passed": True, "live_trading_locked": True, "no_add_order_detected": True},
        "preflight": {"preflight_status": "READY_FOR_OPERATOR_CONFIG_REVIEW", "activation_eligible": True},
        "activation_plan": {"activation_eligible": True},
        "audit": {"passed": True, "blockers": []},
        "review": {"blockers": [], "paper_only_labels_valid": True},
        "fresh": {"passed": True, "status": "PASSED"},
        "risk": {"current_clean": True, "legacy_present": False},
        "approval": {"approval_status": "ELIGIBLE_FOR_OPERATOR_REVIEW"},
        "readiness": {"decision": "OBSERVE_ONLY", "early_recovery_count": 0},
    }
    data.update(overrides)
    return data


def test_decision_blocked_when_safety_audit_fails() -> None:
    """Safety audit failure blocks."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(safety={"passed": False, "live_trading_locked": True, "no_add_order_detected": True}))

    assert report["decision"] == "BLOCKED"


def test_decision_blocked_when_addorder_detected() -> None:
    """Forbidden live order token blocks."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(safety={"passed": True, "live_trading_locked": True, "no_add_order_detected": False}))

    assert report["decision"] == "BLOCKED"


def test_decision_blocked_when_live_trading_unlocked() -> None:
    """Unlocked live trading blocks."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(safety={"passed": True, "live_trading_locked": False, "no_add_order_detected": True}))

    assert report["decision"] == "BLOCKED"


def test_decision_fix_guardrails_when_audit_fails() -> None:
    """Controlled paper audit failure needs guardrail repair."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(audit={"passed": False, "blockers": ["bad"]}))

    assert report["decision"] == "FIX_GUARDRAILS"


def test_decision_fix_guardrails_when_review_has_unsafe_records() -> None:
    """Controlled paper review blockers need guardrail repair."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(review={"blockers": ["unsafe"]}))

    assert report["decision"] == "FIX_GUARDRAILS"


def test_decision_collects_more_when_fresh_validation_insufficient() -> None:
    """Fresh validation insufficiency requests more observations."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(fresh={"passed": False, "status": "INSUFFICIENT_DATA"}))

    assert report["decision"] == "COLLECT_MORE_OBSERVATIONS"


def test_decision_fix_guardrails_when_current_risk_dirty() -> None:
    """Current risk dirt is a guardrail issue."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(risk={"current_clean": False, "legacy_present": False}))

    assert report["decision"] == "FIX_GUARDRAILS"


def test_legacy_warnings_do_not_block_when_allowed() -> None:
    """Legacy audit warnings do not block by themselves."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(risk={"current_clean": True, "legacy_present": True}))

    assert report["decision"] == "CONFIG_REVIEW_DISABLED"
    assert report["legacy_warnings_present"] is True


def test_decision_collects_more_when_observation_count_low() -> None:
    """Low observation count requests more data."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(count=1), summaries=summaries())

    assert report["decision"] == "COLLECT_MORE_OBSERVATIONS"


def test_decision_continue_observation_only_without_strong_buy() -> None:
    """No STRONG_BUY keeps observation-only."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(category="NEUTRAL"), summaries=summaries())

    assert report["decision"] == "CONTINUE_OBSERVATION_ONLY"


def test_decision_continue_observation_only_without_risk_approval() -> None:
    """No risk approvals keeps observation-only."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(approved=False), summaries=summaries())

    assert report["decision"] == "CONTINUE_OBSERVATION_ONLY"


def test_decision_continue_observation_only_when_approval_not_eligible() -> None:
    """Approval gate non-eligible keeps observation-only."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries(approval={"approval_status": "NOT_READY"}))

    assert report["decision"] == "CONTINUE_OBSERVATION_ONLY"


def test_decision_config_review_disabled_when_all_conditions_pass() -> None:
    """All technical checks still stop at disabled config review by default."""
    report = ControlledPaperPreflightReviewService().decide(runs=runs(), summaries=summaries())

    assert report["decision"] == "CONFIG_REVIEW_DISABLED"
    assert report["allow_config_review"] is False


def test_decision_eligible_for_config_review_with_synthetic_full_eligibility() -> None:
    """Synthetic config can reach config-review eligibility only."""
    report = ControlledPaperPreflightReviewService(settings=settings(controlled_paper_decision_allow_config_review=True)).decide(runs=runs(), summaries=summaries())

    assert report["decision"] == "ELIGIBLE_FOR_CONFIG_REVIEW"
    assert report["allow_config_review"] is True


def test_phase38_never_allows_activation_or_live_review() -> None:
    """Decision report never allows activation or live review."""
    report = ControlledPaperPreflightReviewService(settings=settings(controlled_paper_decision_allow_config_review=True)).decide(runs=runs(), summaries=summaries())

    assert report["allow_paper_activation"] is False
    assert report["allow_live_review"] is False
    assert report["paper_trade_execution_allowed_now"] is False


def test_decision_package_includes_required_summaries() -> None:
    """Decision package includes dependency summaries."""
    package = ControlledPaperPreflightReviewService().package()

    assert "decision_report" in package
    assert "preflight_summary" in package
    assert "activation_plan_summary" in package
    assert "audit_summary" in package
    assert "review_summary" in package
    assert "approval_summary" in package
    assert "readiness_summary" in package
    assert "fresh_validation_summary" in package
    assert "risk_hygiene_summary" in package
