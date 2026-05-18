"""Controlled paper preflight tests."""

from app.config import Settings
from app.observation.controlled_paper_preflight import ControlledPaperPreflightService


def settings(**updates):
    """Build settings overrides."""
    return Settings(_env_file=None).model_copy(update=updates)


def result(category="STRONG_BUY", approved=True):
    """Build observation result."""
    return {"signal": {"category": category}, "risk_decision": {"approved": approved}}


def runs(category="STRONG_BUY", approved=True, count=5):
    """Build completed runs."""
    return [{"status": "completed", "results": [result(category, approved) for _ in range(4)]} for _ in range(count)]


def summaries(**overrides):
    """Build clean summaries."""
    data = {
        "safety": {"passed": True, "live_trading_locked": True, "no_add_order_detected": True},
        "audit": {"passed": True, "blockers": []},
        "review": {"blockers": [], "paper_only_labels_valid": True},
        "fresh": {"passed": True, "status": "PASSED"},
        "risk": {"current_clean": True, "legacy_present": False},
        "approval": {"approval_status": "ELIGIBLE_FOR_OPERATOR_REVIEW"},
        "readiness": {"decision": "OBSERVE_ONLY"},
    }
    data.update(overrides)
    return data


def test_preflight_returns_disabled_if_preflight_disabled() -> None:
    """Disabled preflight returns DISABLED."""
    report = ControlledPaperPreflightService(settings=settings(controlled_paper_preflight_enabled=False)).evaluate(runs=[], summaries=summaries())

    assert report["preflight_status"] == "DISABLED"
    assert report["activation_eligible"] is False


def test_preflight_blocks_when_safety_audit_fails() -> None:
    """Safety audit failure blocks."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries(safety={"passed": False, "live_trading_locked": True, "no_add_order_detected": True}))

    assert report["preflight_status"] == "BLOCKED"


def test_preflight_blocks_when_addorder_detected() -> None:
    """Forbidden live order token blocks."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries(safety={"passed": True, "live_trading_locked": True, "no_add_order_detected": False}))

    assert report["preflight_status"] == "BLOCKED"


def test_preflight_blocks_when_live_trading_unlocked() -> None:
    """Unlocked live trading blocks."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries(safety={"passed": True, "live_trading_locked": False, "no_add_order_detected": True}))

    assert report["preflight_status"] == "BLOCKED"


def test_preflight_blocks_when_controlled_paper_audit_fails() -> None:
    """Audit failure blocks."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries(audit={"passed": False, "blockers": ["bad"]}))

    assert report["preflight_status"] == "BLOCKED"


def test_preflight_blocks_when_review_detects_unsafe_records() -> None:
    """Review blockers block."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries(review={"blockers": ["bad labels"]}))

    assert report["preflight_status"] == "BLOCKED"


def test_preflight_not_ready_when_fresh_validation_insufficient() -> None:
    """Fresh validation insufficiency is not ready."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries(fresh={"passed": False, "status": "INSUFFICIENT_DATA"}))

    assert report["preflight_status"] == "NOT_READY"


def test_preflight_blocks_when_current_risk_dirty() -> None:
    """Current risk dirt blocks."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries(risk={"current_clean": False, "legacy_present": False}))

    assert report["preflight_status"] == "BLOCKED"


def test_preflight_warns_but_does_not_block_legacy_warnings() -> None:
    """Legacy warnings do not block when allowed."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries(risk={"current_clean": True, "legacy_present": True}))

    assert report["preflight_status"] == "READY_FOR_OPERATOR_CONFIG_REVIEW"
    assert report["legacy_warnings_present"] is True


def test_preflight_observe_only_with_no_strong_buy() -> None:
    """No STRONG_BUY keeps observe-only."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(category="NEUTRAL"), summaries=summaries())

    assert report["preflight_status"] == "OBSERVE_ONLY"


def test_preflight_observe_only_with_no_risk_approved() -> None:
    """No risk approvals keeps observe-only."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(approved=False), summaries=summaries())

    assert report["preflight_status"] == "OBSERVE_ONLY"


def test_preflight_ready_for_operator_config_review_with_clean_data() -> None:
    """Clean synthetic data reaches ready for review."""
    report = ControlledPaperPreflightService().evaluate(runs=runs(), summaries=summaries())

    assert report["preflight_status"] == "READY_FOR_OPERATOR_CONFIG_REVIEW"
    assert report["activation_eligible"] is True
    assert report["paper_trade_execution_allowed_now"] is False
    assert report["config_change_required"] is True


def test_activation_plan_is_read_only_and_lists_required_flags() -> None:
    """Activation plan is read-only and lists flags/rollback."""
    service = ControlledPaperPreflightService()
    plan = service.activation_plan(service.evaluate(runs=runs(), summaries=summaries()))

    assert plan["activation_eligible"] is True
    assert "CONTROLLED_PAPER_OBSERVATION_ENABLED" in plan["required_config_flags"]
    assert "ENABLE_LIVE_TRADING" in plan["flags_that_must_remain_false"]
    assert plan["rollback_steps"]


def test_preflight_package_includes_required_summaries() -> None:
    """Package includes all summaries."""
    package = ControlledPaperPreflightService().package()

    assert "preflight_report" in package
    assert "activation_plan" in package
    assert "audit_summary" in package
    assert "review_summary" in package
    assert "approval_summary" in package
    assert "readiness_summary" in package
    assert "fresh_validation_summary" in package
    assert "risk_hygiene_summary" in package
