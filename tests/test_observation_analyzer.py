"""Observation analyzer calibration tests."""

from app.calibration.observation_analyzer import ObservationAnalyzer


def observation(symbol="BTC/USD", score=54, category="NEUTRAL", blockers=None, warnings=None, reasons=None):
    """Build a synthetic observation result."""
    return {
        "symbol": symbol,
        "signal": {
            "symbol": symbol,
            "score": score,
            "category": category,
            "risk_level": "HIGH",
            "blockers": blockers or [],
            "warnings": warnings or [],
            "reasons": reasons or [],
            "component_scores": {"momentum": 8},
        },
        "blockers": blockers or [],
        "warnings": warnings or [],
        "reasons": reasons or [],
    }


def test_observation_analyzer_handles_empty_observations() -> None:
    """Empty observations produce a clean report."""
    report = ObservationAnalyzer().analyze_runs([]).to_dict()

    assert report["observations_analyzed"] == 0
    assert report["symbols_analyzed"] == 0
    assert report["overall_average_score"] is None
    assert "No paper observation data" in report["conclusion"]


def test_observation_analyzer_summarizes_one_symbol() -> None:
    """Analyzer summarizes one symbol."""
    summary = ObservationAnalyzer().analyze_symbol("SUI/USD", [observation("SUI/USD", 54), observation("SUI/USD", 50)]).to_dict()

    assert summary["symbol"] == "SUI/USD"
    assert summary["observations_count"] == 2
    assert summary["average_score"] == 52.0
    assert summary["neutral_count"] == 2


def test_observation_analyzer_dedupes_repeated_blockers() -> None:
    """Repeated blockers inside one observation are deduped."""
    result = observation(blockers=["close at or below EMA 200", "close at or below EMA 200"])
    distribution = ObservationAnalyzer().calculate_blocker_distribution([result])

    assert distribution["close at or below EMA 200"] == 1


def test_observation_analyzer_calculates_category_distribution() -> None:
    """Category distribution counts signal categories."""
    distribution = ObservationAnalyzer().calculate_category_distribution([observation(category="NEUTRAL"), observation(category="WEAK")])

    assert distribution["NEUTRAL"] == 1
    assert distribution["WEAK"] == 1


def test_observation_analyzer_detects_dominant_ema_200_blocker() -> None:
    """EMA 200 blocker dominance creates a finding."""
    runs = [{"results": [observation("BTC/USD", 44, "WEAK", ["close at or below EMA 200"]), observation("ETH/USD", 50, "NEUTRAL", ["close <= ema_200"])]}]
    report = ObservationAnalyzer().analyze_runs(runs).to_dict()

    assert any(finding["finding_type"] == "DOMINANT_EMA_200_BLOCKER" for finding in report["findings"])
    assert report["symbol_summaries"][0]["ema_200_blocker_rate"] == 1.0


def test_observation_analyzer_detects_low_score_bottleneck() -> None:
    """Low score bottleneck summary is deterministic."""
    results = [observation(score=54), observation(score=50), observation(score=44), observation(score=40)]
    bottleneck = ObservationAnalyzer().detect_score_bottlenecks(results)

    assert bottleneck["consistently_low"] is True
    assert bottleneck["low_score_rate"] == 1.0

