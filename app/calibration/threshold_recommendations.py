"""Read-only threshold recommendation logic."""

from __future__ import annotations

from app.calibration.calibration_models import CalibrationFinding, SymbolCalibrationSummary, ThresholdRecommendation
from app.config import Settings, get_settings


class ThresholdRecommendationEngine:
    """Build analysis-only calibration recommendations."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize recommendation engine."""
        self.settings = settings or get_settings()

    def build_recommendations(self, summaries: list[SymbolCalibrationSummary], observations_count: int) -> list[ThresholdRecommendation]:
        """Return recommendations without mutating thresholds."""
        recommendations: list[ThresholdRecommendation] = []
        confidence = self._confidence(observations_count)
        affected_by_ema = [summary.symbol for summary in summaries if summary.ema_200_blocker_rate >= self.settings.calibration_warn_ema200_blocker_rate]
        if affected_by_ema:
            recommendations.append(
                ThresholdRecommendation(
                    parameter_name="EARLY_RECOVERY_WATCHLIST",
                    current_value=False,
                    suggested_value="add observation-only tag",
                    reason="EMA 200 is a dominant blocker; consider tracking early recovery candidates without removing the EMA 200 trade filter.",
                    confidence=confidence,
                    sample_size=observations_count,
                )
            )
        low_score_symbols = [summary.symbol for summary in summaries if summary.low_score_rate >= self.settings.calibration_warn_low_score_rate]
        if low_score_symbols:
            recommendations.append(
                ThresholdRecommendation(
                    parameter_name="TREND_COMPONENT_WEIGHTING_REVIEW",
                    current_value="current Crypto Hunter scoring",
                    suggested_value="manual review only",
                    reason="Scores are consistently below BUY_WATCH/STRONG_BUY levels; review trend weighting after a larger observation sample.",
                    confidence=confidence,
                    sample_size=observations_count,
                )
            )
        if 0 < observations_count < self.settings.calibration_min_sample_size_for_changes:
            recommendations.append(
                ThresholdRecommendation(
                    parameter_name="MIN_SAMPLE_SIZE_FOR_CHANGES",
                    current_value=observations_count,
                    suggested_value=f"collect at least {self.settings.calibration_min_sample_size_for_changes} observations",
                    reason="The sample is too small for threshold changes. Continue observation before changing live or paper decision rules.",
                    confidence="LOW",
                    sample_size=observations_count,
                )
            )
        return recommendations

    def build_findings(self, summaries: list[SymbolCalibrationSummary], observations_count: int) -> list[CalibrationFinding]:
        """Return calibration findings from symbol summaries."""
        findings: list[CalibrationFinding] = []
        ema_symbols = [summary.symbol for summary in summaries if summary.ema_200_blocker_rate >= self.settings.calibration_warn_ema200_blocker_rate]
        if ema_symbols:
            findings.append(
                CalibrationFinding(
                    severity="MEDIUM",
                    finding_type="DOMINANT_EMA_200_BLOCKER",
                    message="EMA 200 is the dominant blocker for several observed symbols.",
                    affected_symbols=ema_symbols,
                    evidence={"warn_rate": self.settings.calibration_warn_ema200_blocker_rate},
                    recommendation="Add an observation-only early recovery watchlist tag; do not remove the EMA 200 trade requirement.",
                )
            )
        low_score_symbols = [summary.symbol for summary in summaries if summary.low_score_rate >= self.settings.calibration_warn_low_score_rate]
        if low_score_symbols:
            severity = "LOW" if observations_count < self.settings.calibration_min_sample_size_for_changes else "MEDIUM"
            findings.append(
                CalibrationFinding(
                    severity=severity,
                    finding_type="LOW_SCORE_BOTTLENECK",
                    message="Most observed signals are below trade-consideration scores.",
                    affected_symbols=low_score_symbols,
                    evidence={"warn_rate": self.settings.calibration_warn_low_score_rate, "sample_size": observations_count},
                    recommendation="Keep observing; review trend and momentum component balance only after sufficient samples.",
                )
            )
        if observations_count == 0:
            findings.append(
                CalibrationFinding(
                    severity="LOW",
                    finding_type="NO_OBSERVATION_DATA",
                    message="No observation results are available for calibration.",
                    recommendation="Run paper observation manually before reviewing strategy calibration.",
                )
            )
        return findings

    def _confidence(self, observations_count: int) -> str:
        """Return recommendation confidence from sample size."""
        if observations_count < self.settings.calibration_min_sample_size_for_changes:
            return "LOW"
        if observations_count < self.settings.calibration_min_sample_size_for_changes * 3:
            return "MEDIUM"
        return "HIGH"

