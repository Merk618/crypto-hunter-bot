"""Strategy calibration report tests."""

from app.calibration.strategy_calibration_report import StrategyCalibrationReportBuilder


def test_strategy_calibration_report_says_more_data_needed_for_one_run() -> None:
    """One observation run is not enough to change thresholds."""
    runs = [{"results": [{"symbol": "BTC/USD", "signal": {"score": 44, "category": "WEAK", "blockers": ["close at or below EMA 200"]}}]}]

    report = StrategyCalibrationReportBuilder().build(runs)

    assert "Only one observation run" in report["conclusion"]
    assert report["threshold_recommendations"]
    assert all(not recommendation["auto_apply_allowed"] for recommendation in report["threshold_recommendations"])


def test_strategy_calibration_report_handles_neutral_and_weak_observations() -> None:
    """NEUTRAL and WEAK observations are summarized."""
    runs = [{"results": [
        {"symbol": "SUI/USD", "signal": {"score": 54, "category": "NEUTRAL", "blockers": ["close at or below EMA 200"]}},
        {"symbol": "SOL/USD", "signal": {"score": 40, "category": "WEAK", "blockers": ["close at or below EMA 200"]}},
    ]}]

    report = StrategyCalibrationReportBuilder().build(runs)

    assert report["category_distribution"]["NEUTRAL"] == 1
    assert report["category_distribution"]["WEAK"] == 1
    assert report["observations_analyzed"] == 2

