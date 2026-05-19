"""Unified read-only reports across Crypto, Stock, and Options Hunter."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.journal.journal_filters import dedupe_candidates, filter_production_records
from app.observation.clean_observation_verifier import CleanObservationVerifier
from app.observation.controlled_paper_audit import ControlledPaperAuditService
from app.observation.controlled_paper_observation import ControlledPaperObservationService
from app.observation.controlled_paper_preflight import ControlledPaperPreflightService
from app.observation.controlled_paper_preflight_review import ControlledPaperPreflightReviewService
from app.observation.controlled_paper_review import ControlledPaperReviewService
from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.observation.fresh_observation_validator import FreshObservationValidator
from app.observation.observation_continuation import ObservationContinuationService
from app.observation.paper_trade_approval_gate import PaperTradeApprovalGate
from app.observation.paper_trade_readiness import PaperTradeReadinessService
from app.observation.signal_quality_review import SignalQualityReviewService
from app.reporting.candidate_summary import candidate_from_crypto_signal, candidate_from_early_recovery, candidate_from_ranked_option, candidate_from_stock_result
from app.risk.risk_record_hygiene import RiskRecordHygiene
from app.reporting.dashboard_service import DashboardService
from app.stock_hunter.stock_hunter_service import StockHunterService


class UnifiedReportService:
    """Aggregate read-only summaries for the future YucaTanaTrades frontend."""

    def __init__(
        self,
        settings: Settings | None = None,
        dashboard_service: DashboardService | None = None,
        stock_service: StockHunterService | None = None,
        safety_audit: SafetyAudit | None = None,
    ) -> None:
        """Initialize report dependencies."""
        self.settings = settings or get_settings()
        self.dashboard_service = dashboard_service or DashboardService()
        self.stock_service = stock_service or StockHunterService(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)

    def get_unified_dashboard_summary(self) -> dict:
        """Return one compact read-only dashboard summary."""
        return {
            "overview": self._safe(lambda: self.dashboard_service.get_overview().to_dict(), {}),
            "top_candidates": self.get_top_candidates(),
            "risk_safety": self.get_system_health_summary(),
            "generated_at": self._now(),
            "source": "yucatanatrades_unified_summary_v1",
        }

    def get_top_candidates(self) -> dict:
        """Return normalized top candidates across asset classes."""
        crypto = self._crypto_candidates()
        early_recovery = self._early_recovery_candidates()
        stock = self._stock_candidates()
        options = self._option_candidates()
        return {
            "crypto": dedupe_candidates([candidate.to_dict() for candidate in crypto]),
            "early_recovery": dedupe_candidates([candidate.to_dict() for candidate in early_recovery]),
            "stocks": dedupe_candidates([candidate.to_dict() for candidate in stock]),
            "options": dedupe_candidates([candidate.to_dict() for candidate in options]),
            "generated_at": self._now(),
            "source": "yucatanatrades_top_candidates_v1",
        }

    def get_daily_briefing(self) -> dict:
        """Return a daily briefing-ready summary."""
        top = self.get_top_candidates()
        health = self.get_system_health_summary()
        return {
            "title": "YucaTanaTrades Daily Briefing",
            "top_candidates": top,
            "system_health": health,
            "warnings": self._briefing_warnings(top, health),
            "generated_at": self._now(),
            "source": "yucatanatrades_daily_briefing_v1",
        }

    def get_system_health_summary(self) -> dict:
        """Return risk and safety summary without secrets."""
        risk = self._safe(lambda: self.dashboard_service.get_risk_summary().to_dict(), {})
        safety = self._safe(lambda: self.safety_audit.run().to_dict(), {"passed": False, "warnings": ["safety audit unavailable"]})
        return {
            "risk": risk,
            "risk_record_hygiene": self._safe(lambda: RiskRecordHygiene().summary(limit=100), {"passed": True, "inconsistency_count": 0}),
            "legacy_aware_risk_readiness": self._safe(lambda: RiskRecordHygiene().legacy_aware_readiness(limit=100), {"passed": True, "current_clean": True}),
            "clean_observation_verification": self._safe(lambda: CleanObservationVerifier(settings=self.settings).verify(), {"passed": False, "warnings": ["clean observation verification unavailable"]}),
            "fresh_observation_validation": self._safe(lambda: FreshObservationValidator(settings=self.settings).validate(), {"passed": False, "status": "UNAVAILABLE"}),
            "paper_trade_approval_gate": self._safe(lambda: PaperTradeApprovalGate(settings=self.settings).evaluate(), {"approval_status": "NOT_READY", "eligible_for_operator_review": False, "paper_trade_observation_enabled": False}),
            "controlled_paper_observation": self._safe(lambda: ControlledPaperObservationService(settings=self.settings).status(), {"enabled": False, "paper_trade_observation_enabled": False}),
            "controlled_paper_review": self._safe(lambda: ControlledPaperReviewService(settings=self.settings).review(), {"paper_trades_created": 0, "recent_runs_count": 0}),
            "controlled_paper_audit": self._safe(lambda: ControlledPaperAuditService(settings=self.settings).audit(), {"passed": True, "blockers": []}),
            "controlled_paper_preflight": self._safe(lambda: ControlledPaperPreflightService(settings=self.settings).evaluate(), {"preflight_status": "NOT_READY", "activation_eligible": False}),
            "controlled_paper_decision": self._safe(lambda: ControlledPaperPreflightReviewService(settings=self.settings).decide(), {"decision": "CONTINUE_OBSERVATION_ONLY", "allow_paper_activation": False, "allow_live_review": False}),
            "signal_quality_review": self._safe(lambda: SignalQualityReviewService(settings=self.settings).review(), {"observations_analyzed": 0, "strong_buy_count": 0, "risk_approved_count": 0}),
            "observation_continuation_plan": self._safe(lambda: ObservationContinuationService(settings=self.settings).plan(), {"decision": "CONTINUE_OBSERVATION_ONLY", "paper_trades_allowed": False, "live_review_allowed": False}),
            "paper_trade_readiness": self._safe(lambda: PaperTradeReadinessService(settings=self.settings).check(), {"ready": False, "decision": "NOT_READY"}),
            "safety": {
                "passed": bool(safety.get("passed", False)),
                "live_trading_locked": bool(safety.get("live_trading_locked", True)),
                "no_add_order_detected": bool(safety.get("no_add_order_detected", True)),
                "no_withdrawal_methods_detected": bool(safety.get("no_withdrawal_methods_detected", True)),
                "blockers": safety.get("blockers", []),
                "warnings": safety.get("warnings", []),
            },
            "generated_at": self._now(),
            "source": "yucatanatrades_system_health_v1",
        }

    def _crypto_candidates(self) -> list:
        """Read recent crypto signal records from the journal."""
        report = self._safe(lambda: self.dashboard_service.get_signal_performance(limit=100).to_dict(), {"recent_signals": []})
        records = filter_production_records(report.get("recent_signals", []))
        candidates = [candidate_from_crypto_signal(signal) for signal in records]
        filtered = [candidate for candidate in candidates if candidate.score >= self.settings.alert_min_crypto_score]
        return sorted(filtered, key=lambda item: item.score, reverse=True)[: self.settings.alert_max_items_per_section]

    def _stock_candidates(self) -> list:
        """Read Stock Hunter top candidates."""
        response = self._safe(lambda: self.stock_service.top_candidates(limit=self.settings.alert_max_items_per_section), {"results": []})
        records = filter_production_records(response.get("results", []))
        candidates = [candidate_from_stock_result(result) for result in records]
        filtered = [candidate for candidate in candidates if candidate.score >= self.settings.alert_min_stock_score]
        return sorted(filtered, key=lambda item: item.score, reverse=True)[: self.settings.alert_max_items_per_section]

    def _option_candidates(self) -> list:
        """Read Options Scanner top candidates."""
        response = self._safe(lambda: self.stock_service.top_options(limit=self.settings.alert_max_items_per_section), {"top_candidates": []})
        records = filter_production_records(response.get("top_candidates", []))
        candidates = [candidate_from_ranked_option(contract) for contract in records]
        filtered = [candidate for candidate in candidates if candidate.score >= self.settings.alert_min_options_score]
        return sorted(filtered, key=lambda item: item.score, reverse=True)[: self.settings.alert_max_items_per_section]

    def _early_recovery_candidates(self) -> list:
        """Read observation-only early recovery candidates."""
        response = self._safe(lambda: EarlyRecoveryWatchlistService(settings=self.settings).get_report(), {"candidates": []})
        records = filter_production_records(response.get("candidates", []))
        candidates = [candidate_from_early_recovery(item) for item in records]
        return sorted(candidates, key=lambda item: item.score, reverse=True)[: self.settings.alert_max_items_per_section]

    def _briefing_warnings(self, top: dict, health: dict) -> list[str]:
        """Create briefing warnings."""
        warnings: list[str] = []
        if not top.get("crypto") and not top.get("early_recovery") and not top.get("stocks") and not top.get("options"):
            warnings.append("No candidates met alert thresholds")
        if not health.get("safety", {}).get("passed", False):
            warnings.append("Safety audit is not passing")
        if not health.get("risk_record_hygiene", {}).get("passed", True):
            warnings.append("Risk record hygiene requires review before paper-trade observation.")
        if health.get("legacy_aware_risk_readiness", {}).get("legacy_present"):
            warnings.append("Legacy risk records remain visible as audit warnings.")
        if health.get("clean_observation_verification", {}).get("current_inconsistency_count", 0):
            warnings.append("Current risk record inconsistencies block paper-trade observation readiness.")
        fresh = health.get("fresh_observation_validation", {})
        if fresh.get("status") == "INSUFFICIENT_DATA":
            warnings.append("Fresh observation validation needs a new observation window.")
        if fresh.get("current_inconsistency_count", 0):
            warnings.append("Fresh validation found current risk inconsistencies.")
        if fresh.get("passed"):
            warnings.append("Fresh validation passing does not enable paper or live trading.")
        approval = health.get("paper_trade_approval_gate", {})
        if approval.get("approval_status") in {"BLOCKED", "NOT_READY"}:
            warnings.append("Paper-trade observation approval gate is not ready.")
        if approval.get("eligible_for_operator_review"):
            warnings.append("Paper-trade observation is eligible for operator review only; execution remains disabled.")
        controlled = health.get("controlled_paper_observation", {})
        if not controlled.get("enabled", False):
            warnings.append("Controlled paper observation is disabled by config.")
        if not health.get("controlled_paper_audit", {}).get("passed", True):
            warnings.append("Controlled paper guardrail audit has blockers.")
        preflight = health.get("controlled_paper_preflight", {})
        if preflight.get("preflight_status") in {"OBSERVE_ONLY", "NOT_READY"}:
            warnings.append("Controlled paper preflight is not ready for activation.")
        decision = health.get("controlled_paper_decision", {})
        if decision.get("decision") in {"CONTINUE_OBSERVATION_ONLY", "COLLECT_MORE_OBSERVATIONS"}:
            warnings.append("Controlled paper decision remains observation-only; Phase 38 does not enable paper or live trading.")
        if decision.get("decision") in {"BLOCKED", "FIX_GUARDRAILS"}:
            warnings.append("Controlled paper decision has guardrail blockers.")
        quality = health.get("signal_quality_review", {})
        if quality.get("strong_buy_count", 0) == 0:
            warnings.append("Signal quality review found no STRONG_BUY observations.")
        if quality.get("risk_approved_count", 0) == 0:
            warnings.append("Signal quality review found no risk-approved observations.")
        continuation = health.get("observation_continuation_plan", {})
        if continuation.get("decision") in {"CONTINUE_OBSERVATION_ONLY", "COLLECT_MORE_OBSERVATIONS"}:
            warnings.append("Observation continuation remains read-only; Phase 39 does not change thresholds or enable paper/live trading.")
        return warnings

    def _safe(self, fn, default):
        """Return default when optional data is unavailable."""
        try:
            return fn()
        except Exception:
            return default

    def _now(self) -> str:
        """Return UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()
