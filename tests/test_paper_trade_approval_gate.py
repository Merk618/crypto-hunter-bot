"""Paper-trade approval gate tests."""

from app.observation.paper_trade_approval_gate import PaperTradeApprovalGate


def risk_record(**kwargs):
    """Build synthetic risk record."""
    data = {
        "id": 1,
        "symbol": "BTC/USD",
        "side": "buy",
        "approved": True,
        "approved_quantity": 0.01,
        "max_quantity": 0.01,
        "risk_amount": 25.0,
        "estimated_notional": 650.0,
        "blockers": [],
        "reasons": ["risk approved"],
        "warnings": [],
        "source": "crypto_hunter_risk_v1",
    }
    data.update(kwargs)
    return data


def observation_result(symbol="BTC/USD", category="STRONG_BUY", approved=True):
    """Build synthetic observation result."""
    return {
        "symbol": symbol,
        "signal": {"symbol": symbol, "score": 84, "category": category},
        "risk_decision": risk_record(symbol=symbol, approved=approved, blockers=[] if approved else ["risk rejected"]),
    }


def runs(count=5, category="STRONG_BUY", approved=True):
    """Build enough completed observation runs."""
    symbols = ["BTC/USD", "ETH/USD", "SOL/USD", "SUI/USD"]
    return [
        {"run_id": f"run-{idx}", "status": "completed", "results": [observation_result(symbol, category, approved) for symbol in symbols]}
        for idx in range(count)
    ]


def safety(passed=True, live_locked=True, token_absent=True):
    """Build safety report."""
    return {"passed": passed, "live_trading_locked": live_locked, "no_add_order_detected": token_absent, "blockers": [] if passed else ["safety failed"]}


def fresh(passed=True, status="PASSED"):
    """Build fresh validation report."""
    return {"passed": passed, "status": status, "current_clean": passed, "current_inconsistency_count": 0}


def test_approval_gate_blocks_when_safety_audit_fails() -> None:
    """Safety failure blocks approval."""
    report = PaperTradeApprovalGate().evaluate(runs=runs(), risk_records=[risk_record()], safety_report=safety(passed=False), fresh_report=fresh())

    assert report["approval_status"] == "BLOCKED"
    assert report["eligible_for_operator_review"] is False


def test_approval_gate_blocks_when_live_trading_not_locked() -> None:
    """Unlocked live trading blocks approval."""
    report = PaperTradeApprovalGate().evaluate(runs=runs(), risk_records=[risk_record()], safety_report=safety(live_locked=False), fresh_report=fresh())

    assert report["approval_status"] == "BLOCKED"
    assert report["live_trading_locked"] is False


def test_approval_gate_blocks_when_live_order_token_detected() -> None:
    """Forbidden live order token detection blocks approval."""
    report = PaperTradeApprovalGate().evaluate(runs=runs(), risk_records=[risk_record()], safety_report=safety(token_absent=False), fresh_report=fresh())

    assert report["approval_status"] == "BLOCKED"
    assert report["add_order_absent"] is False


def test_approval_gate_not_ready_when_fresh_validation_insufficient() -> None:
    """Fresh validation insufficiency is not ready."""
    report = PaperTradeApprovalGate().evaluate(runs=runs(), risk_records=[risk_record()], safety_report=safety(), fresh_report=fresh(False, "INSUFFICIENT_DATA"))

    assert report["approval_status"] == "NOT_READY"


def test_approval_gate_blocks_when_current_risk_dirty() -> None:
    """Current risk inconsistency blocks."""
    dirty = risk_record(approved=False, source="crypto_hunter_risk_v2", approved_quantity=1.0, blockers=["rejected"])
    report = PaperTradeApprovalGate().evaluate(runs=runs(), risk_records=[dirty], safety_report=safety(), fresh_report=fresh())

    assert report["approval_status"] == "BLOCKED"
    assert report["current_risk_clean"] is False


def test_approval_gate_warns_but_does_not_block_legacy_records() -> None:
    """Legacy records warn but do not solely block."""
    legacy = risk_record(approved=False, approved_quantity=1.0, risk_amount=10.0, blockers=["old rejected"])
    report = PaperTradeApprovalGate().evaluate(runs=runs(), risk_records=[legacy], safety_report=safety(), fresh_report=fresh())

    assert report["legacy_warnings_present"] is True
    assert report["approval_status"] == "ELIGIBLE_FOR_OPERATOR_REVIEW"
    assert report["warnings"]


def test_approval_gate_not_ready_with_fewer_than_minimum_observations() -> None:
    """Too few observations is not ready."""
    report = PaperTradeApprovalGate().evaluate(runs=runs(count=1), risk_records=[risk_record()], safety_report=safety(), fresh_report=fresh())

    assert report["approval_status"] == "NOT_READY"


def test_approval_gate_not_ready_with_zero_strong_buy() -> None:
    """No STRONG_BUY observations is not ready."""
    report = PaperTradeApprovalGate().evaluate(runs=runs(category="NEUTRAL"), risk_records=[risk_record()], safety_report=safety(), fresh_report=fresh())

    assert report["approval_status"] == "NOT_READY"
    assert report["strong_buy_count"] == 0


def test_approval_gate_not_ready_with_zero_risk_approved() -> None:
    """No risk-approved observations is not ready."""
    report = PaperTradeApprovalGate().evaluate(runs=runs(approved=False), risk_records=[risk_record()], safety_report=safety(), fresh_report=fresh())

    assert report["approval_status"] == "NOT_READY"
    assert report["risk_approved_count"] == 0


def test_approval_gate_eligible_only_when_all_conditions_pass() -> None:
    """All synthetic conditions can become eligible for operator review only."""
    report = PaperTradeApprovalGate().evaluate(runs=runs(), risk_records=[risk_record()], safety_report=safety(), fresh_report=fresh())

    assert report["approval_status"] == "ELIGIBLE_FOR_OPERATOR_REVIEW"
    assert report["eligible_for_operator_review"] is True
    assert report["approved_for_paper_trade_observation"] is False
    assert report["paper_trade_observation_enabled"] is False


def test_approval_package_includes_required_summaries() -> None:
    """Approval package includes review summaries."""
    package = PaperTradeApprovalGate().package()

    assert "approval" in package
    assert "safety" in package
    assert "fresh_validation" in package
    assert "legacy_aware_risk_readiness" in package
    assert "paper_trade_readiness" in package
