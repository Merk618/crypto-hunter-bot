"""Paper trade observation readiness tests."""

from datetime import datetime, timezone

from app.config import Settings
from app.observation.paper_trade_readiness import PaperTradeReadinessService


class Safety:
    """Safety fake."""

    def __init__(self, passed=True, live_locked=True, add_order_absent=True):
        self.passed = passed
        self.live_locked = live_locked
        self.add_order_absent = add_order_absent

    def run(self):
        return Obj({
            "passed": self.passed,
            "live_trading_locked": self.live_locked,
            "no_add_order_detected": self.add_order_absent,
            "blockers": [] if self.passed else ["safety failed"],
        })


class Obj:
    """to_dict fake."""

    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data


class Hygiene:
    """Risk hygiene fake."""

    def __init__(self, count=0):
        self.count = count

    def summary(self, records=None, limit=500):
        return {"passed": self.count == 0, "inconsistency_count": self.count, "inconsistencies": []}


def result(symbol="BTC/USD", category="NEUTRAL", score=61, risk=False):
    """Build observation result."""
    return {
        "symbol": symbol,
        "action_taken": "observed",
        "signal": {
            "symbol": symbol,
            "score": score,
            "category": category,
            "blockers": ["close at or below EMA 200"],
            "reasons": ["MACD positive momentum"],
            "component_scores": {"momentum": 5},
        },
        "risk_decision": {"approved": risk},
        "blockers": ["close at or below EMA 200"],
        "reasons": ["MACD positive momentum"],
    }


def runs(count=5, category="NEUTRAL", risk=False):
    """Build completed runs."""
    return [
        {
            "run_id": f"run-{idx}",
            "status": "completed",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "results": [result("SUI/USD", category, 61, risk), result("ETH/USD", category, 54, risk), result("BTC/USD", "WEAK", 44, False), result("SOL/USD", "WEAK", 40, False)],
        }
        for idx in range(count)
    ]


def service(safety=None, hygiene=None):
    """Build readiness service."""
    return PaperTradeReadinessService(settings=Settings(), safety_audit=safety or Safety(), risk_hygiene=hygiene or Hygiene())


def test_paper_readiness_blocks_when_safety_audit_fails() -> None:
    """Safety audit failure blocks readiness."""
    report = service(safety=Safety(passed=False)).check(runs=runs())

    assert report["decision"] == "BLOCKED"
    assert report["ready"] is False


def test_paper_readiness_blocks_when_live_not_locked() -> None:
    """Unlocked live trading blocks readiness."""
    report = service(safety=Safety(live_locked=False)).check(runs=runs())

    assert any(check["name"] == "live_trading_locked" and not check["passed"] for check in report["checks"])


def test_paper_readiness_blocks_when_addorder_detected() -> None:
    """AddOrder detection blocks readiness."""
    report = service(safety=Safety(add_order_absent=False)).check(runs=runs())

    assert any(check["name"] == "add_order_absent" and not check["passed"] for check in report["checks"])


def test_paper_readiness_blocks_with_fewer_than_20_observations() -> None:
    """Too few observations block readiness."""
    report = service().check(runs=runs(count=2))

    assert report["observations_analyzed"] == 8
    assert any(check["name"] == "observations" and not check["passed"] for check in report["checks"])


def test_paper_readiness_blocks_without_strong_buy() -> None:
    """No STRONG_BUY blocks paper-trade review."""
    report = service().check(runs=runs())

    assert report["strong_buy_count"] == 0
    assert any(check["name"] == "strong_buy_signals" and not check["passed"] for check in report["checks"])


def test_paper_readiness_blocks_without_risk_approved() -> None:
    """No risk approvals block paper-trade review."""
    report = service().check(runs=runs())

    assert report["risk_approved_count"] == 0
    assert any(check["name"] == "risk_approvals" and not check["passed"] for check in report["checks"])


def test_paper_readiness_blocks_with_risk_inconsistencies() -> None:
    """Risk hygiene inconsistencies block readiness."""
    report = service(hygiene=Hygiene(count=1)).check(runs=runs())

    assert report["risk_record_inconsistencies"] == 1
    assert report["decision"] == "BLOCKED"


def test_paper_readiness_confirms_early_recovery_observe_only() -> None:
    """Early recovery remains observe-only."""
    report = service().check(runs=runs())

    assert report["early_recovery_count"] > 0
    assert any(check["name"] == "early_recovery_observe_only" and check["passed"] for check in report["checks"])


def test_paper_readiness_never_enables_paper_trades_by_default() -> None:
    """Paper-trade observation remains disabled."""
    report = service().check(runs=runs())

    assert report["paper_trade_observation_allowed_now"] is False
    assert any(check["name"] == "paper_trades_disabled" and check["passed"] for check in report["checks"])


def test_paper_readiness_requires_operator_approval() -> None:
    """Operator approval remains required."""
    report = service().check(runs=runs())

    assert report["operator_approval_required"] is True
    assert any(check["name"] == "operator_approval_required" and check["passed"] for check in report["checks"])

