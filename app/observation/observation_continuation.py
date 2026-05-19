"""Observation continuation planning."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.observation.controlled_paper_preflight_review import ControlledPaperPreflightReviewService
from app.observation.signal_quality_models import ObservationContinuationPlan
from app.observation.signal_quality_review import SignalQualityReviewService


class ObservationContinuationService:
    """Recommend the next safe observation step without enabling trading."""

    def __init__(
        self,
        settings: Settings | None = None,
        signal_quality: SignalQualityReviewService | None = None,
        controlled_decision: ControlledPaperPreflightReviewService | None = None,
        safety_audit: SafetyAudit | None = None,
    ) -> None:
        """Initialize continuation dependencies."""
        self.settings = settings or get_settings()
        self.signal_quality = signal_quality or SignalQualityReviewService(settings=self.settings)
        self.controlled_decision = controlled_decision or ControlledPaperPreflightReviewService(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)

    def plan(self, runs: list[dict] | None = None, quality_report: dict | None = None, decision_report: dict | None = None, safety_report: dict | None = None) -> dict:
        """Return read-only continuation plan."""
        quality = quality_report or self.signal_quality.review(runs=runs)
        decision = decision_report or self.controlled_decision.decide(runs=runs)
        safety = safety_report or self.safety_audit.run().to_dict()
        blockers: list[str] = []
        warnings = ["Phase 39 does not change thresholds or enable paper/live trading."]
        if not self.settings.observation_continuation_enabled:
            blockers.append("Observation continuation review is disabled.")
        if not safety.get("passed") or not safety.get("no_add_order_detected") or not safety.get("live_trading_locked"):
            blockers.append("Safety audit, forbidden live order token absence, and live lock must pass.")
        plan_decision = self._decision(quality, decision, safety, blockers)
        reasons = self._reasons(quality, decision)
        if quality.get("early_recovery_count", 0):
            warnings.append("Early recovery candidates remain observe-only.")
        report = ObservationContinuationPlan(
            decision=plan_decision,
            confidence="LOW" if quality.get("observations_analyzed", 0) < self.settings.signal_quality_review_min_observations else "MEDIUM",
            continue_observation_only=plan_decision in {"CONTINUE_OBSERVATION_ONLY", "COLLECT_MORE_OBSERVATIONS", "REVIEW_SIGNAL_COMPONENTS"},
            additional_runs_recommended=self.settings.observation_continuation_target_additional_runs,
            additional_observations_recommended=self.settings.observation_continuation_target_additional_observations,
            threshold_changes_allowed=False,
            paper_trades_allowed=False,
            live_review_allowed=False,
            reasons=reasons,
            blockers=list(dict.fromkeys(blockers)),
            warnings=list(dict.fromkeys(warnings)),
            recommended_next_actions=self._actions(plan_decision, quality),
        )
        return report.to_dict()

    def _decision(self, quality: dict, decision: dict, safety: dict, blockers: list[str]) -> str:
        """Return continuation decision."""
        if blockers:
            return "BLOCKED"
        if quality.get("observations_analyzed", 0) < self.settings.signal_quality_review_min_observations:
            return "COLLECT_MORE_OBSERVATIONS"
        if quality.get("strong_buy_count", 0) == 0:
            return "CONTINUE_OBSERVATION_ONLY"
        if quality.get("risk_approved_count", 0) == 0:
            return "CONTINUE_OBSERVATION_ONLY"
        if quality.get("early_recovery_count", 0) and decision.get("decision") == "CONTINUE_OBSERVATION_ONLY":
            return "REVIEW_SIGNAL_COMPONENTS"
        if decision.get("decision") == "ELIGIBLE_FOR_CONFIG_REVIEW":
            return "READY_FOR_PAPER_REVIEW"
        return "CONTINUE_OBSERVATION_ONLY"

    def _reasons(self, quality: dict, decision: dict) -> list[str]:
        """Return plan reasons."""
        reasons = []
        if quality.get("strong_buy_count", 0) == 0:
            reasons.append("No STRONG_BUY observations have been collected.")
        if quality.get("risk_approved_count", 0) == 0:
            reasons.append("No risk-approved observations have been collected.")
        if quality.get("dominant_blockers"):
            reasons.append("Dominant blockers are still shaping signal quality.")
        if quality.get("early_recovery_count", 0):
            reasons.append("Early recovery candidates exist but remain observe-only.")
        reasons.append(f"Controlled paper decision is {decision.get('decision', 'UNKNOWN')}.")
        return reasons

    def _actions(self, decision: str, quality: dict) -> list[str]:
        """Return next actions."""
        actions = ["Continue persisted observation windows.", "Keep thresholds unchanged.", "Do not enable paper trades or live trading."]
        if decision == "COLLECT_MORE_OBSERVATIONS":
            actions.insert(0, "Collect a larger persisted observation window.")
        if decision == "CONTINUE_OBSERVATION_ONLY":
            actions.insert(0, "Stay observation-only until repeated STRONG_BUY and risk-approved observations appear.")
        if quality.get("dominant_blockers"):
            actions.append("Review trend component behavior manually while keeping EMA 200 required.")
        return list(dict.fromkeys(actions))
