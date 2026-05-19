"""Signal quality review tests."""

from app.observation.signal_quality_review import SignalQualityReviewService


def result(symbol="BTC/USD", score=50, category="NEUTRAL", approved=False, blockers=None, warnings=None, reasons=None):
    """Build observation result."""
    return {
        "symbol": symbol,
        "signal": {"score": score, "category": category, "blockers": blockers or [], "warnings": warnings or [], "reasons": reasons or []},
        "risk_decision": {"approved": approved},
        "blockers": blockers or [],
        "warnings": warnings or [],
        "reasons": reasons or [],
    }


def runs(results=None, count=5):
    """Build completed runs."""
    payload = results or [result()]
    return [{"status": "completed", "results": payload} for _ in range(count)]


def test_signal_quality_empty_report_when_no_observations() -> None:
    """Empty history returns insufficient report."""
    report = SignalQualityReviewService().review(runs=[])

    assert report["observations_analyzed"] == 0
    assert report["blockers"]


def test_signal_quality_counts_strong_buy_buy_watch_neutral_weak() -> None:
    """Signal categories are counted."""
    report = SignalQualityReviewService().review(
        runs=[
            {
                "status": "completed",
                "results": [
                    result(category="STRONG_BUY", score=84),
                    result(category="BUY_WATCH", score=70),
                    result(category="NEUTRAL", score=55),
                    result(category="WEAK", score=44),
                ],
            }
            for _ in range(5)
        ]
    )

    assert report["strong_buy_count"] == 5
    assert report["buy_watch_count"] == 5
    assert report["neutral_count"] == 5
    assert report["weak_count"] == 5


def test_signal_quality_counts_risk_approved() -> None:
    """Risk approvals are counted."""
    report = SignalQualityReviewService().review(runs=runs([result(approved=True), result(approved=False)], count=5))

    assert report["risk_approved_count"] == 5


def test_signal_quality_identifies_ema200_dominant_blocker() -> None:
    """EMA 200 dominant blocker is detected."""
    report = SignalQualityReviewService().review(runs=runs([result(blockers=["close at or below EMA 200"])], count=5))

    assert any("EMA 200" in item["text"] for item in report["dominant_blockers"])
    assert any(item["finding_type"] == "DOMINANT_EMA_200_BLOCKER" for item in report["findings"])


def test_signal_quality_identifies_repeated_early_recovery_candidates() -> None:
    """Early recovery candidates are counted."""
    payload = [result(symbol="SUI/USD", score=61, category="NEUTRAL", blockers=["close at or below EMA 200"], reasons=["MACD positive"])]
    report = SignalQualityReviewService().review(runs=runs(payload, count=5))

    assert report["early_recovery_count"] >= 1
    assert report["symbol_summaries"][0]["early_recovery_candidate"] is True


def test_signal_quality_identifies_near_buy_watch_symbols() -> None:
    """Near BUY_WATCH scores are counted."""
    report = SignalQualityReviewService().review(runs=runs([result(score=66, category="NEUTRAL")], count=5))

    assert report["near_buy_watch_count"] == 5
    assert report["symbol_summaries"][0]["near_buy_watch_count"] == 5


def test_signal_quality_trend_improving_when_scores_rise() -> None:
    """Rising scores are improving."""
    report = SignalQualityReviewService().review(runs=[{"status": "completed", "results": [result(score=60), result(score=55), result(score=50)]} for _ in range(5)])

    assert report["symbol_summaries"][0]["score_trend"] == "IMPROVING"


def test_signal_quality_trend_deteriorating_when_scores_fall() -> None:
    """Falling scores are deteriorating."""
    report = SignalQualityReviewService().review(runs=[{"status": "completed", "results": [result(score=45), result(score=55), result(score=65)]} for _ in range(5)])

    assert report["symbol_summaries"][0]["score_trend"] == "DETERIORATING"
