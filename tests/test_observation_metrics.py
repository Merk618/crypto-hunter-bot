"""Observation metrics tests."""

from app.observation.observation_metrics import (
    calculate_calibration_readiness,
    detect_repeated_watchlist_candidates,
    summarize_blockers,
    summarize_categories,
    summarize_scores_by_symbol,
)


def result(symbol="BTC/USD", score=54, category="NEUTRAL", blockers=None):
    """Build synthetic result."""
    return {"symbol": symbol, "signal": {"score": score, "category": category, "blockers": blockers or []}, "blockers": blockers or []}


def test_observation_metrics_calculate_average_max_latest_score() -> None:
    """Score metrics are calculated by symbol."""
    scores = summarize_scores_by_symbol([result(score=50), result(score=60)])

    assert scores["BTC/USD"]["average_score"] == 55.0
    assert scores["BTC/USD"]["max_score"] == 60.0
    assert scores["BTC/USD"]["latest_score"] == 50.0


def test_observation_metrics_aggregate_categories_and_blockers() -> None:
    """Categories and blockers aggregate."""
    results = [result(category="NEUTRAL", blockers=["close at or below EMA 200"]), result(category="WEAK", blockers=["close at or below EMA 200"])]

    assert summarize_categories(results)["NEUTRAL"] == 1
    assert summarize_blockers(results)["close at or below EMA 200"] == 2


def test_repeated_watchlist_candidates_detected() -> None:
    """Repeated neutral-or-better candidates are detected."""
    candidates = detect_repeated_watchlist_candidates([result(score=54), result(score=58), result("ETH/USD", 40, "WEAK")])

    assert candidates[0]["symbol"] == "BTC/USD"
    assert candidates[0]["count"] == 2


def test_calibration_readiness_not_ready_and_ready() -> None:
    """Readiness follows run thresholds."""
    assert calculate_calibration_readiness(1, 3) == "NOT_READY"
    assert calculate_calibration_readiness(3, 3) == "PARTIAL"
    assert calculate_calibration_readiness(6, 3) == "READY_FOR_REVIEW"

