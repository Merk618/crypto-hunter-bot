"""Controlled paper preflight review and operator decision."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.observation.controlled_paper_audit import ControlledPaperAuditService
from app.observation.controlled_paper_decision_models import ControlledPaperDecisionCheck, ControlledPaperDecisionPackage, ControlledPaperObservationDecisionReport
from app.observation.controlled_paper_preflight import ControlledPaperPreflightService
from app.observation.controlled_paper_review import ControlledPaperReviewService
from app.observation.fresh_observation_validator import FreshObservationValidator
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_metrics import flatten_results
from app.observation.paper_trade_approval_gate import PaperTradeApprovalGate
from app.observation.paper_trade_readiness import PaperTradeReadinessService
from app.risk.risk_record_hygiene import RiskRecordHygiene


class ControlledPaperPreflightReviewService:
    """Review Phase 37 preflight outputs and produce a read-only operator decision."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        safety_audit: SafetyAudit | None = None,
        preflight: ControlledPaperPreflightService | None = None,
        audit_service: ControlledPaperAuditService | None = None,
        review_service: ControlledPaperReviewService | None = None,
        fresh_validator: FreshObservationValidator | None = None,
        approval_gate: PaperTradeApprovalGate | None = None,
        readiness: PaperTradeReadinessService | None = None,
        risk_hygiene: RiskRecordHygiene | None = None,
    ) -> None:
        """Initialize decision dependencies."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.risk_hygiene = risk_hygiene or RiskRecordHygiene(settings=self.settings)
        self.audit_service = audit_service or ControlledPaperAuditService(settings=self.settings)
        self.review_service = review_service or ControlledPaperReviewService(settings=self.settings)
        self.fresh_validator = fresh_validator or FreshObservationValidator(settings=self.settings, hydration=self.hydration, hygiene=self.risk_hygiene)
        self.approval_gate = approval_gate or PaperTradeApprovalGate(settings=self.settings, hydration=self.hydration, safety_audit=self.safety_audit, risk_hygiene=self.risk_hygiene)
        self.readiness = readiness or PaperTradeReadinessService(settings=self.settings, hydration=self.hydration, safety_audit=self.safety_audit, risk_hygiene=self.risk_hygiene)
        self.preflight = preflight or ControlledPaperPreflightService(
            settings=self.settings,
            hydration=self.hydration,
            safety_audit=self.safety_audit,
            audit_service=self.audit_service,
            review_service=self.review_service,
            fresh_validator=self.fresh_validator,
            approval_gate=self.approval_gate,
            readiness=self.readiness,
            risk_hygiene=self.risk_hygiene,
        )

    def decide(self, runs: list[dict] | None = None, summaries: dict | None = None) -> dict:
        """Return the controlled paper observation decision report."""
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        summaries = summaries or self._summaries(runs)
        completed = [run for run in runs if run.get("status") == "completed"]
        results = flatten_results(completed)
        strong_buy_count = sum(1 for result in results if (result.get("signal") or {}).get("category") == "STRONG_BUY")
        risk_approved_count = sum(1 for result in results if (result.get("risk_decision") or {}).get("approved"))
        early_recovery_count = int(summaries.get("readiness", {}).get("early_recovery_count") or 0)
        checks = self._checks(summaries, completed, results, strong_buy_count, risk_approved_count)
        blockers = [blocker for check in checks for blocker in check.blockers]
        warnings = [warning for check in checks for warning in check.warnings]
        decision = self._decision(checks, summaries, completed, results, strong_buy_count, risk_approved_count)
        report = ControlledPaperObservationDecisionReport(
            decision=decision,
            confidence=self._confidence(decision, len(results)),
            allow_config_review=decision == "ELIGIBLE_FOR_CONFIG_REVIEW",
            allow_paper_activation=False,
            allow_live_review=False,
            current_mode="observe_only",
            preflight_status=str(summaries["preflight"].get("preflight_status")),
            activation_eligible=bool(summaries["preflight"].get("activation_eligible")),
            approval_gate_status=str(summaries["approval"].get("approval_status")),
            paper_trade_readiness_status=str(summaries["readiness"].get("decision")),
            fresh_validation_status=str(summaries["fresh"].get("status")),
            controlled_paper_audit_passed=bool(summaries["audit"].get("passed")),
            controlled_paper_review_clean=not bool(summaries["review"].get("blockers")),
            current_risk_clean=bool(summaries["risk"].get("current_clean")),
            legacy_warnings_present=bool(summaries["risk"].get("legacy_present")),
            completed_runs_analyzed=len(completed),
            observations_analyzed=len(results),
            strong_buy_count=strong_buy_count,
            risk_approved_count=risk_approved_count,
            early_recovery_count=early_recovery_count,
            controlled_paper_enabled_now=self.settings.controlled_paper_observation_enabled,
            buys_allowed_now=self.settings.controlled_paper_observation_allow_buys,
            sells_allowed_now=self.settings.controlled_paper_observation_allow_sells,
            paper_trade_execution_allowed_now=False,
            checks=[check.to_dict() for check in checks],
            warnings=list(dict.fromkeys(warnings)),
            blockers=list(dict.fromkeys(blockers)),
            recommended_next_actions=self._actions(decision),
        )
        return report.to_dict()

    def checks(self) -> dict:
        """Return decision checks only."""
        report = self.decide()
        return {"decision": report["decision"], "checks": report["checks"], "source": "crypto_hunter_controlled_paper_decision_checks_v1"}

    def package(self) -> dict:
        """Return full controlled paper decision package."""
        runs = self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        summaries = self._summaries(runs)
        report = self.decide(runs=runs, summaries=summaries)
        return ControlledPaperDecisionPackage(
            decision_report=report,
            preflight_summary=summaries["preflight"],
            activation_plan_summary=summaries["activation_plan"],
            audit_summary=summaries["audit"],
            review_summary=summaries["review"],
            approval_summary=summaries["approval"],
            readiness_summary=summaries["readiness"],
            fresh_validation_summary=summaries["fresh"],
            risk_hygiene_summary=summaries["risk"],
            observation_summary={
                "completed_runs": report["completed_runs_analyzed"],
                "observations": report["observations_analyzed"],
                "strong_buy_count": report["strong_buy_count"],
                "risk_approved_count": report["risk_approved_count"],
                "early_recovery_count": report["early_recovery_count"],
            },
            final_recommendation=self._final_recommendation(report),
        ).to_dict()

    def next_step(self) -> dict:
        """Return compact operator next step."""
        report = self.decide()
        return {
            "decision": report["decision"],
            "allow_config_review": report["allow_config_review"],
            "allow_paper_activation": False,
            "allow_live_review": False,
            "next_step": (report.get("recommended_next_actions") or ["Continue observation-only mode."])[0],
            "source": "crypto_hunter_controlled_paper_next_step_v1",
        }

    def _summaries(self, runs: list[dict]) -> dict:
        """Build dependency summaries."""
        completed = [run for run in runs if run.get("status") == "completed"]
        preflight_report = self.preflight.evaluate(runs=runs)
        return {
            "safety": self.safety_audit.run().to_dict(),
            "preflight": preflight_report,
            "activation_plan": self.preflight.activation_plan(preflight_report),
            "audit": self.audit_service.audit(),
            "review": self.review_service.review(),
            "fresh": self.fresh_validator.validate(runs=runs),
            "risk": self.risk_hygiene.legacy_aware_readiness(),
            "approval": self.approval_gate.evaluate(runs=runs),
            "readiness": self.readiness.check(runs=completed),
        }

    def _checks(self, summaries: dict, completed: list[dict], results: list[dict], strong_buy_count: int, risk_approved_count: int) -> list[ControlledPaperDecisionCheck]:
        """Build decision checks."""
        safety = summaries["safety"]
        return [
            self._check("safety_audit", bool(safety.get("passed")), "Safety audit must pass", safety, hard=True),
            self._check("add_order_absent", bool(safety.get("no_add_order_detected")), "Forbidden live order token must be absent", safety, hard=True),
            self._check("live_trading_locked", bool(safety.get("live_trading_locked")), "Live trading must remain locked", safety, hard=True),
            self._check("controlled_paper_audit", bool(summaries["audit"].get("passed")), "Controlled paper audit must pass", summaries["audit"], hard=True),
            self._check("controlled_paper_review", not summaries["review"].get("blockers"), "Controlled paper review must be clean", summaries["review"], hard=True),
            self._check("fresh_validation", bool(summaries["fresh"].get("passed")), "Fresh validation must pass", summaries["fresh"]),
            self._check("current_risk_clean", bool(summaries["risk"].get("current_clean")), "Current risk hygiene must be clean", summaries["risk"], hard=True),
            self._check("completed_runs", len(completed) >= self.settings.controlled_paper_decision_min_completed_runs, "Minimum completed runs required", {"completed_runs": len(completed)}),
            self._check("observations", len(results) >= self.settings.controlled_paper_decision_min_observations, "Minimum observations required", {"observations": len(results)}),
            self._check("strong_buy", strong_buy_count >= self.settings.controlled_paper_decision_min_strong_buy_count or not self.settings.controlled_paper_decision_require_strong_buy, "STRONG_BUY observations required", {"strong_buy_count": strong_buy_count}),
            self._check("risk_approved", risk_approved_count >= self.settings.controlled_paper_decision_min_risk_approved_count or not self.settings.controlled_paper_decision_require_risk_approved, "Risk-approved observations required", {"risk_approved_count": risk_approved_count}),
            self._check("approval_gate", summaries["approval"].get("approval_status") == "ELIGIBLE_FOR_OPERATOR_REVIEW" or not self.settings.controlled_paper_decision_require_approval_eligible, "Approval gate must be eligible", summaries["approval"]),
            self._check("preflight", summaries["preflight"].get("preflight_status") == "READY_FOR_OPERATOR_CONFIG_REVIEW" or not self.settings.controlled_paper_decision_require_preflight, "Preflight must be ready for config review", summaries["preflight"]),
            self._check("activation_disabled", not self.settings.controlled_paper_decision_allow_activation, "Phase 38 must not allow paper activation", {}, hard=True),
        ]

    def _check(self, name: str, passed: bool, message: str, metadata: dict, hard: bool = False) -> ControlledPaperDecisionCheck:
        """Build one decision check."""
        return ControlledPaperDecisionCheck(
            name=name,
            passed=passed,
            status="PASS" if passed else ("BLOCKED" if hard else "NOT_READY"),
            message=message,
            blockers=[] if passed else [message],
            warnings=[],
            metadata=metadata,
        )

    def _decision(self, checks: list[ControlledPaperDecisionCheck], summaries: dict, completed: list[dict], results: list[dict], strong_buy_count: int, risk_approved_count: int) -> str:
        """Return Phase 38 operator decision."""
        if not self.settings.controlled_paper_preflight_review_enabled:
            return "BLOCKED"
        safety = summaries["safety"]
        if not safety.get("passed") or not safety.get("no_add_order_detected") or not safety.get("live_trading_locked"):
            return "BLOCKED"
        if not summaries["audit"].get("passed") or summaries["review"].get("blockers"):
            return "FIX_GUARDRAILS"
        if not summaries["fresh"].get("passed"):
            return "COLLECT_MORE_OBSERVATIONS"
        if self.settings.controlled_paper_decision_require_current_risk_clean and not summaries["risk"].get("current_clean"):
            return "FIX_GUARDRAILS"
        if len(completed) < self.settings.controlled_paper_decision_min_completed_runs or len(results) < self.settings.controlled_paper_decision_min_observations:
            return "COLLECT_MORE_OBSERVATIONS"
        if strong_buy_count < self.settings.controlled_paper_decision_min_strong_buy_count:
            return "CONTINUE_OBSERVATION_ONLY"
        if risk_approved_count < self.settings.controlled_paper_decision_min_risk_approved_count:
            return "CONTINUE_OBSERVATION_ONLY"
        if summaries["approval"].get("approval_status") != "ELIGIBLE_FOR_OPERATOR_REVIEW":
            return "CONTINUE_OBSERVATION_ONLY"
        if not self.settings.controlled_paper_decision_allow_config_review:
            return "CONFIG_REVIEW_DISABLED"
        return "ELIGIBLE_FOR_CONFIG_REVIEW"

    def _confidence(self, decision: str, observations: int) -> str:
        """Return confidence label."""
        if decision in {"BLOCKED", "FIX_GUARDRAILS"}:
            return "HIGH"
        if observations < self.settings.controlled_paper_decision_min_observations:
            return "LOW"
        return "MEDIUM"

    def _actions(self, decision: str) -> list[str]:
        """Return recommended next actions."""
        actions = {
            "BLOCKED": ["Resolve safety blockers before any controlled paper review."],
            "FIX_GUARDRAILS": ["Fix controlled paper guardrails or current risk hygiene before continuing."],
            "COLLECT_MORE_OBSERVATIONS": ["Run more persisted observation windows before controlled paper review."],
            "CONTINUE_OBSERVATION_ONLY": ["Continue observation-only mode until repeated STRONG_BUY and risk-approved observations appear."],
            "CONFIG_REVIEW_DISABLED": ["All technical checks can be reviewed, but config review remains disabled in Phase 38."],
            "ELIGIBLE_FOR_CONFIG_REVIEW": ["Eligible for future operator config review only; do not enable paper activation in this phase."],
        }.get(decision, ["Continue observation-only mode."])
        actions.append("Phase 38 does not enable paper or live trading.")
        return list(dict.fromkeys(actions))

    def _final_recommendation(self, report: dict) -> str:
        """Return final package recommendation."""
        decision = report.get("decision")
        if decision == "ELIGIBLE_FOR_CONFIG_REVIEW":
            return "Eligible for future manual config review only; paper activation remains disabled."
        if decision == "CONFIG_REVIEW_DISABLED":
            return "Technical criteria may be met, but config review is disabled and no trades are enabled."
        if decision == "COLLECT_MORE_OBSERVATIONS":
            return "Collect more fresh observations before reviewing controlled paper mode."
        if decision == "FIX_GUARDRAILS":
            return "Fix guardrail or risk hygiene blockers before continuing."
        return "Remain in observation-only mode."
