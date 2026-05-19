"""Standalone operator service."""

from __future__ import annotations

from app.alerts.alert_service import AlertService
from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.core.app_state import AppState
from app.core.safety_audit import SafetyAudit
from app.execution.paper_broker import PaperBroker
from app.operator.command_summary import CommandSummaryBuilder
from app.operator.operator_models import OperatorStatus
from app.operator.startup_checks import StartupChecks
from app.observation.fresh_observation_validator import FreshObservationValidator
from app.observation.extended_observation_plan import ExtendedObservationPlanService
from app.observation.observation_continuation import ObservationContinuationService
from app.observation.paper_trade_approval_gate import PaperTradeApprovalGate
from app.observation.controlled_paper_observation import ControlledPaperObservationService
from app.observation.controlled_paper_audit import ControlledPaperAuditService
from app.observation.controlled_paper_preflight import ControlledPaperPreflightService
from app.observation.controlled_paper_preflight_review import ControlledPaperPreflightReviewService
from app.observation.controlled_paper_review import ControlledPaperReviewService
from app.observation.signal_quality_review import SignalQualityReviewService
from app.observation.strategy_review_checkpoint import StrategyReviewCheckpointService
from app.reporting.unified_report_service import UnifiedReportService


class OperatorService:
    """Read-only operator facade for local standalone operation."""

    def __init__(
        self,
        settings: Settings | None = None,
        app_state: AppState | None = None,
        safety_audit: SafetyAudit | None = None,
        alert_service: AlertService | None = None,
        unified_report_service: UnifiedReportService | None = None,
        paper_broker: PaperBroker | None = None,
        moomoo_client: MooMooReadOnlyClient | None = None,
        startup_checks: StartupChecks | None = None,
        command_builder: CommandSummaryBuilder | None = None,
        fresh_validator: FreshObservationValidator | None = None,
        approval_gate: PaperTradeApprovalGate | None = None,
        controlled_paper: ControlledPaperObservationService | None = None,
        controlled_review: ControlledPaperReviewService | None = None,
        controlled_audit: ControlledPaperAuditService | None = None,
        controlled_preflight: ControlledPaperPreflightService | None = None,
        controlled_decision: ControlledPaperPreflightReviewService | None = None,
        signal_quality: SignalQualityReviewService | None = None,
        observation_continuation: ObservationContinuationService | None = None,
        strategy_checkpoint: StrategyReviewCheckpointService | None = None,
        extended_observation_plan: ExtendedObservationPlanService | None = None,
    ) -> None:
        """Initialize operator dependencies."""
        self.settings = settings or get_settings()
        self.app_state = app_state or AppState(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.alert_service = alert_service or AlertService(settings=self.settings)
        self.unified_report_service = unified_report_service or UnifiedReportService(settings=self.settings)
        self.paper_broker = paper_broker or PaperBroker(settings=self.settings)
        self.moomoo_client = moomoo_client or MooMooReadOnlyClient(settings=self.settings)
        self.startup_checks = startup_checks or StartupChecks(settings=self.settings, safety_audit=self.safety_audit, alert_service=self.alert_service)
        self.command_builder = command_builder or CommandSummaryBuilder()
        self.fresh_validator = fresh_validator or FreshObservationValidator(settings=self.settings)
        self.approval_gate = approval_gate or PaperTradeApprovalGate(settings=self.settings)
        self.controlled_paper = controlled_paper or ControlledPaperObservationService(settings=self.settings)
        self.controlled_review = controlled_review or ControlledPaperReviewService(settings=self.settings)
        self.controlled_audit = controlled_audit or ControlledPaperAuditService(settings=self.settings)
        self.controlled_preflight = controlled_preflight or ControlledPaperPreflightService(settings=self.settings)
        self.controlled_decision = controlled_decision or ControlledPaperPreflightReviewService(settings=self.settings)
        self.signal_quality = signal_quality or SignalQualityReviewService(settings=self.settings)
        self.observation_continuation = observation_continuation or ObservationContinuationService(settings=self.settings, signal_quality=self.signal_quality, controlled_decision=self.controlled_decision)
        self.strategy_checkpoint = strategy_checkpoint or StrategyReviewCheckpointService(settings=self.settings, signal_quality=self.signal_quality, controlled_decision=self.controlled_decision)
        self.extended_observation_plan = extended_observation_plan or ExtendedObservationPlanService(settings=self.settings, checkpoint_service=self.strategy_checkpoint)

    def get_operator_status(self) -> dict:
        """Return standalone operator status."""
        safety = self._safe(lambda: self.safety_audit.run().to_dict(), {"passed": False, "live_trading_locked": False, "blockers": ["safety audit unavailable"], "warnings": []})
        account = self._safe(lambda: self.paper_broker.get_account_summary(), {})
        alerts = self._safe(lambda: self.alert_service.get_alert_status(), {})
        moomoo = self._safe(lambda: self.moomoo_client.get_health().to_dict(), {"enabled": False, "connected": False, "read_only": True})
        blockers = list(safety.get("blockers") or [])
        warnings = list(safety.get("warnings") or [])
        status = OperatorStatus(
            mode=str(self.settings.bot_mode.value),
            backend_healthy=not blockers,
            live_trading_locked=bool(safety.get("live_trading_locked", False)),
            kraken_status={"public_data": "not_checked", "reason": "operator status avoids network calls by default"},
            moomoo_status=moomoo,
            paper_status={"mode": "paper", "safe": True, "account": account},
            journal_status={"enabled": self.settings.enable_trade_journal},
            alerts_status=alerts,
            safety_audit_passed=bool(safety.get("passed", False)),
            warnings=warnings + self._fresh_warnings(),
            blockers=blockers,
        )
        return status.to_dict()

    def run_startup_checks(self) -> dict:
        """Run startup checks."""
        return self.startup_checks.run().to_dict()

    def get_safe_command_summary(self) -> dict:
        """Return safe local commands."""
        return self.command_builder.build().to_dict()

    def get_daily_operator_briefing(self) -> dict:
        """Return daily operator briefing."""
        briefing = self._safe(lambda: self.unified_report_service.get_daily_briefing(), {"warnings": ["daily briefing unavailable"]})
        return {
            "operator_status": self.get_operator_status(),
            "daily_briefing": briefing,
            "next_actions": self.get_next_recommended_actions(),
            "source": "crypto_hunter_operator_daily_briefing_v1",
        }

    def get_next_recommended_actions(self) -> list[str]:
        """Return next recommended safe actions."""
        startup = self._safe(lambda: self.startup_checks.run().to_dict(), {"recommended_actions": ["Run startup checks"]})
        actions = list(startup.get("recommended_actions") or ["Run /operator/startup-checks"])
        fresh = self._safe(lambda: self.fresh_validator.validate(), {"recommended_next_actions": []})
        actions.extend(fresh.get("recommended_next_actions") or [])
        approval = self._safe(lambda: self.approval_gate.evaluate(), {"recommended_next_actions": []})
        actions.extend(approval.get("recommended_next_actions") or [])
        controlled = self._safe(lambda: self.controlled_paper.evaluate(), {})
        if controlled.get("status") == "DISABLED_BY_CONFIG":
            actions.append("Controlled paper observation is disabled by config.")
        audit = self._safe(lambda: self.controlled_audit.audit(), {"recommended_next_actions": []})
        actions.extend(audit.get("recommended_next_actions") or [])
        preflight = self._safe(lambda: self.controlled_preflight.evaluate(), {"recommended_next_actions": []})
        actions.extend(preflight.get("recommended_next_actions") or [])
        decision = self._safe(lambda: self.controlled_decision.decide(), {"recommended_next_actions": []})
        actions.extend(decision.get("recommended_next_actions") or [])
        quality = self._safe(lambda: self.signal_quality.review(), {"recommended_next_actions": []})
        actions.extend(quality.get("recommended_next_actions") or [])
        continuation = self._safe(lambda: self.observation_continuation.plan(), {"recommended_next_actions": []})
        actions.extend(continuation.get("recommended_next_actions") or [])
        checkpoint = self._safe(lambda: self.strategy_checkpoint.checkpoint(), {"recommended_next_actions": []})
        actions.extend(checkpoint.get("recommended_next_actions") or [])
        extended = self._safe(lambda: self.extended_observation_plan.plan(), {"recommended_commands": []})
        if extended.get("observe_only"):
            actions.append("Use the extended observation plan before any further paper-review discussion.")
        return list(dict.fromkeys(actions))

    def _fresh_warnings(self) -> list[str]:
        """Return fresh observation warnings for operator status."""
        fresh = self._safe(lambda: self.fresh_validator.validate(), {})
        warnings = list(fresh.get("warnings") or [])
        if fresh.get("status") == "INSUFFICIENT_DATA":
            warnings.append("Fresh observation validation needs a new observation window.")
        if fresh.get("passed"):
            warnings.append("Fresh validation passing does not enable paper or live trading.")
        approval = self._safe(lambda: self.approval_gate.evaluate(), {})
        if approval.get("approval_status") in {"BLOCKED", "NOT_READY"}:
            warnings.append("Paper-trade approval gate is not ready.")
        if approval.get("eligible_for_operator_review"):
            warnings.append("Paper-trade observation is eligible for operator review only; execution remains disabled.")
        controlled = self._safe(lambda: self.controlled_paper.status(), {})
        if not controlled.get("enabled", False):
            warnings.append("Controlled paper observation is disabled by config.")
        audit = self._safe(lambda: self.controlled_audit.audit(), {})
        if not audit.get("passed", True):
            warnings.append("Controlled paper guardrail audit has blockers.")
        preflight = self._safe(lambda: self.controlled_preflight.evaluate(), {})
        if preflight.get("preflight_status") in {"OBSERVE_ONLY", "NOT_READY"}:
            warnings.append("Controlled paper preflight is not ready for activation.")
        decision = self._safe(lambda: self.controlled_decision.decide(), {})
        if decision.get("decision") in {"CONTINUE_OBSERVATION_ONLY", "COLLECT_MORE_OBSERVATIONS"}:
            warnings.append("Controlled paper decision remains observation-only.")
        if decision.get("decision") in {"BLOCKED", "FIX_GUARDRAILS"}:
            warnings.append("Controlled paper decision has guardrail blockers.")
        quality = self._safe(lambda: self.signal_quality.review(), {})
        if quality.get("strong_buy_count", 0) == 0:
            warnings.append("Signal quality review has no STRONG_BUY observations.")
        continuation = self._safe(lambda: self.observation_continuation.plan(), {})
        if continuation.get("decision") in {"CONTINUE_OBSERVATION_ONLY", "COLLECT_MORE_OBSERVATIONS"}:
            warnings.append("Observation continuation remains read-only.")
        checkpoint = self._safe(lambda: self.strategy_checkpoint.checkpoint(), {})
        if checkpoint.get("decision") in {"CONTINUE_OBSERVATION_ONLY", "EXTEND_OBSERVATION_WINDOW"}:
            warnings.append("Strategy checkpoint recommends observation-only or extended observation.")
        return warnings

    def _safe(self, fn, default):
        """Return default when optional data is unavailable."""
        try:
            return fn()
        except Exception:
            return default
