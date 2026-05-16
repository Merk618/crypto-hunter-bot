"""Threshold recommendation tests."""

from app.calibration.calibration_models import SymbolCalibrationSummary
from app.calibration.threshold_recommendations import ThresholdRecommendationEngine


def test_threshold_recommendations_do_not_auto_apply() -> None:
    """Recommendations are analysis-only."""
    summary = SymbolCalibrationSummary(symbol="BTC/USD", observations_count=1, average_score=44, max_score=44, min_score=44, latest_score=44, ema_200_blocker_rate=1.0, low_score_rate=1.0)
    recommendations = ThresholdRecommendationEngine().build_recommendations([summary], observations_count=1)

    assert recommendations
    assert all(not recommendation.auto_apply_allowed for recommendation in recommendations)


def test_threshold_recommendations_low_confidence_with_small_sample_size() -> None:
    """Small samples force LOW confidence."""
    summary = SymbolCalibrationSummary(symbol="ETH/USD", observations_count=1, average_score=50, max_score=50, min_score=50, latest_score=50, low_score_rate=1.0)
    recommendations = ThresholdRecommendationEngine().build_recommendations([summary], observations_count=1)

    assert all(recommendation.confidence == "LOW" for recommendation in recommendations)

