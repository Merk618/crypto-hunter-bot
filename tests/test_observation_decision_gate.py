"""Strategy decision gate tests."""

from app.calibration.strategy_decision_gate import StrategyDecisionGate


class Safety:
    """Safety fake."""

    def __init__(self, passed=True):
        self.passed = passed

    def run(self):
        return Obj({"passed": self.passed, "blockers": [] if self.passed else ["safety failed"]})


class Obj:
    """to_dict helper."""

    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data


def observation(symbol="SUI/USD", score=61, category="NEUTRAL"):
    """Build synthetic result."""
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
        "risk_decision": {"approved": False},
        "blockers": ["close at or below EMA 200"],
        "reasons": ["MACD positive momentum"],
    }


def runs(count=5):
    """Build completed observation runs with four symbols each."""
    symbols = [("SUI/USD", 61, "NEUTRAL"), ("ETH/USD", 54, "NEUTRAL"), ("BTC/USD", 44, "WEAK"), ("SOL/USD", 40, "WEAK")]
    return [{"status": "completed", "results": [observation(symbol, score, category) for symbol, score, category in symbols]} for _ in range(count)]


def test_decision_gate_returns_keep_observing_below_20_observations() -> None:
    """Below 20 observations, keep observing."""
    report = StrategyDecisionGate(safety_audit=Safety()).evaluate(runs(4)).to_dict()

    assert report["decision"] == "KEEP_OBSERVING"
    assert report["paper_trade_observation_allowed"] is False
    assert report["live_review_allowed"] is False


def test_decision_gate_returns_early_recovery_for_current_pattern() -> None:
    """Twenty EMA-blocked observations with repeated neutral candidates add watchlist tag."""
    report = StrategyDecisionGate(safety_audit=Safety()).evaluate(runs(5)).to_dict()

    assert report["decision"] == "ADD_EARLY_RECOVERY_WATCHLIST"
    assert report["confidence"] == "MEDIUM"
    assert report["paper_trade_observation_allowed"] is False
    assert report["live_review_allowed"] is False
    assert report["strongest_symbols"][0]["symbol"] == "SUI/USD"
    assert any(candidate["symbol"] == "SUI/USD" for candidate in report["early_recovery_candidates"])


def test_decision_gate_blocks_when_safety_audit_fails() -> None:
    """Failed safety audit blocks decision."""
    report = StrategyDecisionGate(safety_audit=Safety(passed=False)).evaluate(runs(5)).to_dict()

    assert report["decision"] == "BLOCKED"
    assert report["live_review_allowed"] is False

