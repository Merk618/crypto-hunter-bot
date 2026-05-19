"""Strategy review checkpoint service."""

from __future__ import annotations

from app.calibration.strategy_calibration_report import StrategyCalibrationReportBuilder
from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.observation.controlled_paper_preflight_review import ControlledPaperPreflightReviewService
from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.observation.fresh_observation_validator import FreshObservationValidator
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_metrics import flatten_results
from app.observation.paper_trade_readiness import PaperTradeReadinessService
from app.observation.signal_quality_review import SignalQualityReviewService
from app.observation.strategy_review_models import StrategyReviewCheckpointReport
from app.risk.risk_record_hygiene import RiskRecordHygiene


class StrategyReviewCheckpointService:
    """Combine observation and safety summaries into one formal checkpoint."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        safety_audit: SafetyAudit | None = None,
        signal_quality: SignalQualityReviewService | None = None,
        calibration: StrategyCalibrationReportBuilder | None = None,
        controlled_decision: ControlledPaperPreflightReviewService | None = None,
        readiness: PaperTradeReadinessService | None = None,
        fresh_validator: FreshObservationValidator | None = None,
        risk_hygiene: RiskRecordHygiene | None = None,
        early_recovery: EarlyRecoveryWatchlistService | None = None,
    ) -> None:
        """Initialize checkpoint dependencies."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.signal_quality = signal_quality or SignalQualityReviewService(settings=self.settings, hydration=self.hydration)
        self.calibration = calibration or StrategyCalibrationReportBuilder(settings=self.settings)
        self.controlled_decision = controlled_decision or ControlledPaperPreflightReviewService(settings=self.settings, hydration=self.hydration, safety_audit=self.safety_audit)
        self.readiness = readiness or PaperTradeReadinessService(settings=self.settings, hydration=self.hydration, safety_audit=self.safety_audit)
        self.fresh_validator = fresh_validator or FreshObservationValidator(settings=self.settings, hydration=self.hydration)
        self.risk_hygiene = risk_hygiene or RiskRecordHygiene(settings=self.settings)
        self.early_recovery = early_recovery or EarlyRecoveryWatchlistService(settings=self.settings, hydration=self.hydration)

    def checkpoint(self, runs: list[dict] | None = None, summaries: dict | None = None) -> dict:
        """Return formal strategy checkpoint."""
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        completed = [run for run in runs if run.get("status") == "completed"]
        results = flatten_results(completed)
        summaries = summaries or self._summaries(runs)
        safety = summaries["safety"]
        quality = summaries["signal_quality"]
        blockers = self._blockers(safety, quality)
        decision = self._decision(safety, quality, blockers)
        early = summaries.get("early_recovery", {})
        report = StrategyReviewCheckpointReport(
            checkpoint_status="BLOCKED" if blockers else "REVIEWED",
            decision=decision,
            confidence=self._confidence(decision, quality.get("observations_analyzed", len(results))),
            observations_analyzed=int(quality.get("observations_analyzed", len(results)) or 0),
            completed_runs_analyzed=int(quality.get("completed_runs_analyzed", len(completed)) or 0),
            average_score=quality.get("average_score"),
            max_score=quality.get("max_score"),
            strong_buy_count=int(quality.get("strong_buy_count", 0) or 0),
            buy_watch_count=int(quality.get("buy_watch_count", 0) or 0),
            neutral_count=int(quality.get("neutral_count", 0) or 0),
            weak_count=int(quality.get("weak_count", 0) or 0),
            risk_approved_count=int(quality.get("risk_approved_count", 0) or 0),
            early_recovery_count=int(quality.get("early_recovery_count", 0) or 0),
            dominant_blockers=quality.get("dominant_blockers", []),
            strongest_symbols=self._strongest_symbols(quality, early),
            signal_quality_summary=quality,
            calibration_summary=summaries["calibration"],
            controlled_paper_decision_summary=summaries["controlled_decision"],
            paper_trade_readiness_summary=summaries["readiness"],
            fresh_validation_summary=summaries["fresh"],
            risk_hygiene_summary=summaries["risk"],
            safety_summary=safety,
            threshold_changes_allowed=False,
            threshold_change_recommended=False,
            paper_trades_allowed=False,
            paper_trade_recommended=False,
            live_review_allowed=False,
            live_review_recommended=False,
            warnings=self._warnings(quality, early),
            blockers=blockers,
            findings=self._findings(quality, summaries),
            recommended_next_actions=self._actions(decision),
        )
        return report.to_dict()

    def package(self) -> dict:
        """Return checkpoint package with extended summaries."""
        runs = self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        summaries = self._summaries(runs)
        report = self.checkpoint(runs=runs, summaries=summaries)
        return {
            "checkpoint": report,
            "signal_quality": summaries["signal_quality"],
            "calibration": summaries["calibration"],
            "early_recovery": summaries["early_recovery"],
            "controlled_paper_decision": summaries["controlled_decision"],
            "paper_trade_readiness": summaries["readiness"],
            "fresh_validation": summaries["fresh"],
            "risk_hygiene": summaries["risk"],
            "safety": summaries["safety"],
            "source": "crypto_hunter_strategy_review_package_v1",
        }

    def _summaries(self, runs: list[dict]) -> dict:
        """Build checkpoint dependency summaries."""
        completed = [run for run in runs if run.get("status") == "completed"]
        safety = self.safety_audit.run().to_dict()
        return {
            "safety": safety,
            "signal_quality": self.signal_quality.review(runs=runs),
            "calibration": self.calibration.build(completed),
            "early_recovery": self.early_recovery.get_report() if runs is None else EarlyRecoveryWatchlistService(settings=self.settings, runs=completed).get_report(),
            "controlled_decision": self.controlled_decision.decide(runs=runs),
            "readiness": self.readiness.check(runs=completed),
            "fresh": self.fresh_validator.validate(runs=runs),
            "risk": self.risk_hygiene.legacy_aware_readiness(),
        }

    def _blockers(self, safety: dict, quality: dict) -> list[str]:
        """Return hard blockers."""
        blockers = []
        if self.settings.strategy_review_require_safety_audit and not safety.get("passed"):
            blockers.append("Safety audit must pass.")
        if self.settings.strategy_review_require_addorder_absent and not safety.get("no_add_order_detected"):
            blockers.append("Forbidden live order token must be absent.")
        if self.settings.strategy_review_require_live_locked and not safety.get("live_trading_locked"):
            blockers.append("Live trading must remain locked.")
        if not self.settings.strategy_review_checkpoint_enabled:
            blockers.append("Strategy review checkpoint is disabled.")
        return blockers

    def _decision(self, safety: dict, quality: dict, blockers: list[str]) -> str:
        """Return checkpoint decision."""
        if blockers:
            return "BLOCKED"
        if quality.get("observations_analyzed", 0) < self.settings.strategy_review_min_observations:
            return "EXTEND_OBSERVATION_WINDOW"
        if quality.get("strong_buy_count", 0) == 0:
            return "CONTINUE_OBSERVATION_ONLY"
        if quality.get("risk_approved_count", 0) == 0:
            return "CONTINUE_OBSERVATION_ONLY"
        if any(summary.get("score_trend") == "DETERIORATING" for summary in quality.get("symbol_summaries", [])):
            return "REVIEW_SIGNAL_COMPONENTS"
        return "EXTEND_OBSERVATION_WINDOW"

    def _confidence(self, decision: str, observations: int) -> str:
        """Return confidence label."""
        if decision == "BLOCKED":
            return "HIGH"
        if observations < self.settings.strategy_review_min_observations:
            return "LOW"
        return "MEDIUM"

    def _strongest_symbols(self, quality: dict, early: dict) -> list[dict]:
        """Return strongest symbols from signal quality and early recovery."""
        summaries = sorted(quality.get("symbol_summaries", []), key=lambda item: (item.get("max_score") or 0, item.get("latest_score") or 0), reverse=True)
        symbols = [{"symbol": item.get("symbol"), "max_score": item.get("max_score"), "latest_score": item.get("latest_score"), "source": "signal_quality"} for item in summaries[:5]]
        for candidate in early.get("candidates", [])[:5]:
            if not any(item["symbol"] == candidate.get("symbol") for item in symbols):
                symbols.append({"symbol": candidate.get("symbol"), "max_score": candidate.get("max_score"), "latest_score": candidate.get("latest_score"), "source": "early_recovery"})
        return symbols[:10]

    def _warnings(self, quality: dict, early: dict) -> list[str]:
        """Return checkpoint warnings."""
        warnings = ["Phase 40 does not change thresholds or enable paper/live trading."]
        if early.get("candidates"):
            warnings.append("Early recovery candidates remain observe-only.")
        if quality.get("dominant_blockers"):
            warnings.append("Dominant blockers require manual review while EMA 200 remains required.")
        return list(dict.fromkeys(warnings))

    def _findings(self, quality: dict, summaries: dict) -> list[dict]:
        """Return checkpoint findings."""
        findings = list(quality.get("findings", []))
        if summaries["controlled_decision"].get("decision") in {"CONTINUE_OBSERVATION_ONLY", "COLLECT_MORE_OBSERVATIONS"}:
            findings.append({"finding_type": "CONTROLLED_PAPER_NOT_READY", "message": "Controlled paper decision remains conservative."})
        if summaries["readiness"].get("risk_approved_count", 0) == 0:
            findings.append({"finding_type": "NO_RISK_APPROVALS", "message": "Paper-trade readiness lacks risk-approved observations."})
        return findings

    def _actions(self, decision: str) -> list[str]:
        """Return next actions."""
        actions = {
            "BLOCKED": ["Resolve safety blockers before further strategy review."],
            "EXTEND_OBSERVATION_WINDOW": ["Run an extended persisted observation window before further review."],
            "CONTINUE_OBSERVATION_ONLY": ["Continue observation-only mode until STRONG_BUY and risk-approved observations appear."],
            "REVIEW_SIGNAL_COMPONENTS": ["Manually review signal components while keeping thresholds unchanged."],
            "READY_FOR_PAPER_REVIEW": ["Review only; Phase 40 still does not enable paper trades."],
        }.get(decision, ["Continue observation-only mode."])
        actions.extend(["Keep thresholds unchanged.", "Do not enable paper trades or live trading."])
        return list(dict.fromkeys(actions))
