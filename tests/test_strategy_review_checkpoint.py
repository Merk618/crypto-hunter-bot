"""Strategy review checkpoint tests."""

from app.observation.strategy_review_checkpoint import StrategyReviewCheckpointService


def quality(**updates):
    """Build signal quality summary."""
    data = {
        "observations_analyzed": 20,
        "completed_runs_analyzed": 5,
        "average_score": 55,
        "max_score": 70,
        "strong_buy_count": 1,
        "buy_watch_count": 1,
        "neutral_count": 10,
        "weak_count": 8,
        "risk_approved_count": 1,
        "early_recovery_count": 1,
        "dominant_blockers": [{"text": "close at or below EMA 200", "count": 12}],
        "symbol_summaries": [{"symbol": "SUI/USD", "max_score": 70, "latest_score": 65, "score_trend": "IMPROVING"}],
        "findings": [],
    }
    data.update(updates)
    return data


def summaries(**updates):
    """Build checkpoint summaries."""
    data = {
        "safety": {"passed": True, "live_trading_locked": True, "no_add_order_detected": True},
        "signal_quality": quality(),
        "calibration": {"conclusion": "keep observing"},
        "early_recovery": {"candidates": [{"symbol": "SUI/USD", "max_score": 70, "latest_score": 65}]},
        "controlled_decision": {"decision": "CONTINUE_OBSERVATION_ONLY"},
        "readiness": {"decision": "OBSERVE_ONLY", "risk_approved_count": 1},
        "fresh": {"passed": True, "status": "PASSED"},
        "risk": {"current_clean": True, "legacy_present": True},
    }
    data.update(updates)
    return data


def test_checkpoint_blocks_when_safety_audit_fails() -> None:
    """Safety failure blocks checkpoint."""
    report = StrategyReviewCheckpointService().checkpoint(runs=[], summaries=summaries(safety={"passed": False, "live_trading_locked": True, "no_add_order_detected": True}))

    assert report["decision"] == "BLOCKED"


def test_checkpoint_blocks_when_addorder_detected() -> None:
    """Forbidden live order token blocks checkpoint."""
    report = StrategyReviewCheckpointService().checkpoint(runs=[], summaries=summaries(safety={"passed": True, "live_trading_locked": True, "no_add_order_detected": False}))

    assert report["decision"] == "BLOCKED"


def test_checkpoint_blocks_when_live_trading_unlocked() -> None:
    """Unlocked live trading blocks checkpoint."""
    report = StrategyReviewCheckpointService().checkpoint(runs=[], summaries=summaries(safety={"passed": True, "live_trading_locked": False, "no_add_order_detected": True}))

    assert report["decision"] == "BLOCKED"


def test_checkpoint_recommends_extended_observation_when_sample_small() -> None:
    """Small sample extends observation window."""
    report = StrategyReviewCheckpointService().checkpoint(runs=[], summaries=summaries(signal_quality=quality(observations_analyzed=4)))

    assert report["decision"] == "EXTEND_OBSERVATION_WINDOW"


def test_checkpoint_continues_observe_only_when_strong_buy_zero() -> None:
    """No STRONG_BUY continues observe-only."""
    report = StrategyReviewCheckpointService().checkpoint(runs=[], summaries=summaries(signal_quality=quality(strong_buy_count=0)))

    assert report["decision"] == "CONTINUE_OBSERVATION_ONLY"


def test_checkpoint_continues_observe_only_when_risk_approved_zero() -> None:
    """No risk approvals continues observe-only."""
    report = StrategyReviewCheckpointService().checkpoint(runs=[], summaries=summaries(signal_quality=quality(risk_approved_count=0)))

    assert report["decision"] == "CONTINUE_OBSERVATION_ONLY"


def test_checkpoint_includes_early_recovery_and_dominant_blockers() -> None:
    """Early recovery and blockers are included."""
    report = StrategyReviewCheckpointService().checkpoint(runs=[], summaries=summaries())

    assert report["early_recovery_count"] == 1
    assert report["dominant_blockers"]
    assert report["strongest_symbols"][0]["symbol"] == "SUI/USD"


def test_checkpoint_keeps_trading_and_threshold_recommendations_false() -> None:
    """Phase 40 keeps changes and trading disabled."""
    report = StrategyReviewCheckpointService().checkpoint(runs=[], summaries=summaries())

    assert report["threshold_change_recommended"] is False
    assert report["paper_trade_recommended"] is False
    assert report["live_review_recommended"] is False
    assert report["paper_trades_allowed"] is False
    assert report["live_review_allowed"] is False
