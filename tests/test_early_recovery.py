"""Early recovery classifier tests."""

from app.observation.early_recovery import EarlyRecoveryClassifier


def result(symbol="SUI/USD", score=61, category="NEUTRAL", momentum=True):
    """Build synthetic observation result."""
    reasons = ["MACD positive momentum"] if momentum else []
    components = {"momentum": 5} if momentum else {"momentum": 0}
    return {
        "symbol": symbol,
        "action_taken": "observed",
        "signal": {
            "score": score,
            "category": category,
            "blockers": ["close at or below EMA 200"],
            "warnings": [],
            "reasons": reasons,
            "component_scores": components,
        },
        "risk_decision": {"approved": False},
        "blockers": ["close at or below EMA 200"],
        "reasons": reasons,
    }


def test_early_recovery_identifies_sui_like_candidate() -> None:
    """SUI-like repeated neutral EMA-blocked momentum candidate qualifies."""
    candidates = EarlyRecoveryClassifier().classify_results([result(), result(score=59), result(score=60)])

    assert candidates
    assert candidates[0].symbol == "SUI/USD"
    assert candidates[0].action == "OBSERVE_ONLY"


def test_early_recovery_rejects_weak_low_score_candidate() -> None:
    """Low-score weak candidate is rejected."""
    candidates = EarlyRecoveryClassifier().classify_results([result(score=40, category="WEAK"), result(score=44, category="WEAK")])

    assert candidates == []


def test_early_recovery_requires_momentum_evidence() -> None:
    """Momentum evidence is required by default."""
    candidates = EarlyRecoveryClassifier().classify_results([result(momentum=False), result(score=59, momentum=False)])

    assert candidates == []

