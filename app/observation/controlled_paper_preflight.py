"""Controlled paper activation preflight."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.observation.controlled_paper_audit import ControlledPaperAuditService
from app.observation.controlled_paper_preflight_models import ControlledPaperActivationPlan, ControlledPaperPreflightCheck, ControlledPaperPreflightPackage, ControlledPaperPreflightReport
from app.observation.controlled_paper_review import ControlledPaperReviewService
from app.observation.fresh_observation_validator import FreshObservationValidator
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_metrics import flatten_results
from app.observation.paper_trade_approval_gate import PaperTradeApprovalGate
from app.observation.paper_trade_readiness import PaperTradeReadinessService
from app.risk.risk_record_hygiene import RiskRecordHygiene


class ControlledPaperPreflightService:
    """Read-only preflight for future controlled paper activation."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        safety_audit: SafetyAudit | None = None,
        audit_service: ControlledPaperAuditService | None = None,
        review_service: ControlledPaperReviewService | None = None,
        fresh_validator: FreshObservationValidator | None = None,
        approval_gate: PaperTradeApprovalGate | None = None,
        readiness: PaperTradeReadinessService | None = None,
        risk_hygiene: RiskRecordHygiene | None = None,
    ) -> None:
        """Initialize preflight service."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.risk_hygiene = risk_hygiene or RiskRecordHygiene(settings=self.settings)
        self.audit_service = audit_service or ControlledPaperAuditService(settings=self.settings)
        self.review_service = review_service or ControlledPaperReviewService(settings=self.settings)
        self.fresh_validator = fresh_validator or FreshObservationValidator(settings=self.settings, hydration=self.hydration, hygiene=self.risk_hygiene)
        self.approval_gate = approval_gate or PaperTradeApprovalGate(settings=self.settings, hydration=self.hydration, safety_audit=self.safety_audit, risk_hygiene=self.risk_hygiene)
        self.readiness = readiness or PaperTradeReadinessService(settings=self.settings, hydration=self.hydration, safety_audit=self.safety_audit, risk_hygiene=self.risk_hygiene)

    def evaluate(self, runs: list[dict] | None = None, summaries: dict | None = None) -> dict:
        """Return controlled paper activation preflight report."""
        if not self.settings.controlled_paper_preflight_enabled:
            return self._disabled_report()
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        summaries = summaries or self._summaries(runs)
        results = flatten_results([run for run in runs if run.get("status") == "completed"])
        strong_buy_count = sum(1 for result in results if (result.get("signal") or {}).get("category") == "STRONG_BUY")
        risk_approved_count = sum(1 for result in results if (result.get("risk_decision") or {}).get("approved"))
        checks = self._checks(summaries, runs, results, strong_buy_count, risk_approved_count)
        blockers = [blocker for check in checks for blocker in check.blockers]
        warnings = [warning for check in checks for warning in check.warnings]
        status = self._status(checks, summaries, strong_buy_count, risk_approved_count)
        eligible = status == "READY_FOR_OPERATOR_CONFIG_REVIEW"
        report = ControlledPaperPreflightReport(
            preflight_status=status,
            activation_eligible=eligible,
            config_change_required=True,
            controlled_paper_enabled_now=self.settings.controlled_paper_observation_enabled,
            buys_allowed_now=self.settings.controlled_paper_observation_allow_buys,
            sells_allowed_now=self.settings.controlled_paper_observation_allow_sells,
            paper_trade_execution_allowed_now=False,
            live_review_allowed=False,
            audit_passed=bool(summaries["audit"].get("passed")),
            review_clean=not summaries["review"].get("blockers"),
            fresh_validation_passed=bool(summaries["fresh"].get("passed")),
            current_risk_clean=bool(summaries["risk"].get("current_clean")),
            legacy_warnings_present=bool(summaries["risk"].get("legacy_present")),
            approval_gate_status=str(summaries["approval"].get("approval_status")),
            paper_trade_readiness_status=str(summaries["readiness"].get("decision")),
            completed_runs_analyzed=sum(1 for run in runs if run.get("status") == "completed"),
            observations_analyzed=len(results),
            strong_buy_count=strong_buy_count,
            risk_approved_count=risk_approved_count,
            checks=[check.to_dict() for check in checks],
            warnings=list(dict.fromkeys(warnings)),
            blockers=list(dict.fromkeys(blockers)),
            recommended_next_actions=self._actions(status),
        )
        return report.to_dict()

    def checks(self) -> dict:
        """Return preflight checks only."""
        report = self.evaluate()
        return {"preflight_status": report["preflight_status"], "checks": report["checks"], "source": "crypto_hunter_controlled_paper_preflight_checks_v1"}

    def activation_plan(self, report: dict | None = None) -> dict:
        """Return read-only activation plan."""
        report = report or self.evaluate()
        plan = ControlledPaperActivationPlan(
            activation_eligible=bool(report.get("activation_eligible")),
            current_mode="observe_only",
            required_manual_steps=[
                "Review safety audit, controlled paper audit, fresh validation, risk hygiene, and approval package.",
                "Confirm operator acknowledgement before any future paper-only activation.",
                "Manually update configuration in a future phase only if approval is accepted.",
                "Restart backend and rerun guardrail audit after any future config change.",
            ],
            required_config_flags={
                "CONTROLLED_PAPER_OBSERVATION_ENABLED": "true",
                "CONTROLLED_PAPER_OBSERVATION_ALLOW_BUYS": "true",
                "PAPER_TRADE_OBSERVATION_ENABLED": "true",
            },
            flags_that_must_remain_false={
                "ENABLE_LIVE_TRADING": "false",
                "KRAKEN_PRIVATE_TRADING_ENABLED": "false",
                "CONTROLLED_PAPER_OBSERVATION_ALLOW_SELLS": "false",
                "PAPER_TRADE_OBSERVATION_ALLOW_ENABLE": "false",
            },
            max_notional_per_trade=self.settings.controlled_paper_observation_max_notional_per_trade,
            max_trades_per_run=self.settings.controlled_paper_observation_max_trades_per_run,
            max_trades_per_day=self.settings.controlled_paper_observation_max_trades_per_day,
            safety_warnings=[
                "Activation plan is read-only and does not modify files.",
                "READY_FOR_OPERATOR_CONFIG_REVIEW does not enable paper or live trading.",
                "Live trading remains blocked.",
            ],
            rollback_steps=[
                "Set CONTROLLED_PAPER_OBSERVATION_ENABLED=false.",
                "Set CONTROLLED_PAPER_OBSERVATION_ALLOW_BUYS=false.",
                "Set PAPER_TRADE_OBSERVATION_ENABLED=false.",
                "Restart backend and verify /observation/controlled-paper/audit passes.",
            ],
        )
        return plan.to_dict()

    def package(self) -> dict:
        """Return complete preflight package."""
        runs = self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        summaries = self._summaries(runs)
        report = self.evaluate(runs=runs, summaries=summaries)
        return ControlledPaperPreflightPackage(
            preflight_report=report,
            activation_plan=self.activation_plan(report),
            audit_summary=summaries["audit"],
            review_summary=summaries["review"],
            approval_summary=summaries["approval"],
            readiness_summary=summaries["readiness"],
            fresh_validation_summary=summaries["fresh"],
            risk_hygiene_summary=summaries["risk"],
            final_recommendation=self._final_recommendation(report),
        ).to_dict()

    def _summaries(self, runs: list[dict]) -> dict:
        """Build dependency summaries."""
        return {
            "safety": self.safety_audit.run().to_dict(),
            "audit": self.audit_service.audit(),
            "review": self.review_service.review(),
            "fresh": self.fresh_validator.validate(runs=runs),
            "risk": self.risk_hygiene.legacy_aware_readiness(),
            "approval": self.approval_gate.evaluate(runs=runs),
            "readiness": self.readiness.check(runs=[run for run in runs if run.get("status") == "completed"]),
        }

    def _checks(self, summaries: dict, runs: list[dict], results: list[dict], strong_buy_count: int, risk_approved_count: int) -> list[ControlledPaperPreflightCheck]:
        """Build preflight checks."""
        safety = summaries["safety"]
        return [
            self._check("safety_audit", bool(safety.get("passed")), "Safety audit must pass", safety, hard=True),
            self._check("live_trading_locked", bool(safety.get("live_trading_locked")), "Live trading must remain locked", safety, hard=True),
            self._check("add_order_absent", bool(safety.get("no_add_order_detected")), "Forbidden live order token must be absent", safety, hard=True),
            self._check("controlled_paper_audit", bool(summaries["audit"].get("passed")), "Controlled paper audit must pass", summaries["audit"], hard=True),
            self._check("controlled_paper_review", not summaries["review"].get("blockers"), "Controlled paper review must be clean", summaries["review"], hard=True),
            self._check("fresh_validation", bool(summaries["fresh"].get("passed")), "Fresh validation must pass", summaries["fresh"]),
            self._check("current_risk_clean", bool(summaries["risk"].get("current_clean")), "Current risk hygiene must be clean", summaries["risk"], hard=True),
            self._check("approval_gate", summaries["approval"].get("approval_status") == "ELIGIBLE_FOR_OPERATOR_REVIEW", "Approval gate must be eligible for operator review", summaries["approval"]),
            self._check("completed_runs", sum(1 for run in runs if run.get("status") == "completed") >= self.settings.controlled_paper_preflight_min_completed_runs, "Minimum completed runs required", {}),
            self._check("observations", len(results) >= self.settings.controlled_paper_preflight_min_observations, "Minimum observations required", {}),
            self._check("strong_buy", strong_buy_count >= self.settings.controlled_paper_preflight_min_strong_buy_count, "Repeated STRONG_BUY observations required", {"strong_buy_count": strong_buy_count}),
            self._check("risk_approved", risk_approved_count >= self.settings.controlled_paper_preflight_min_risk_approved_count, "Risk-approved observations required", {"risk_approved_count": risk_approved_count}),
            self._check("disabled_defaults", not self.settings.controlled_paper_observation_enabled and not self.settings.controlled_paper_observation_allow_buys and not self.settings.controlled_paper_observation_allow_sells, "Controlled paper defaults must remain disabled", {}),
            self._check("config_mutation_disabled", not self.settings.controlled_paper_preflight_allow_config_mutation, "Preflight must not mutate config", {}, hard=True),
        ]

    def _check(self, name: str, passed: bool, message: str, metadata: dict, hard: bool = False) -> ControlledPaperPreflightCheck:
        """Build one check."""
        return ControlledPaperPreflightCheck(
            name=name,
            passed=passed,
            status="PASS" if passed else ("BLOCKED" if hard else "NOT_READY"),
            message=message,
            blockers=[] if passed else [message],
            warnings=[],
            metadata=metadata,
        )

    def _status(self, checks: list[ControlledPaperPreflightCheck], summaries: dict, strong_buy_count: int, risk_approved_count: int) -> str:
        """Return preflight status."""
        if any(not check.passed and check.status == "BLOCKED" for check in checks):
            return "BLOCKED"
        if strong_buy_count < self.settings.controlled_paper_preflight_min_strong_buy_count or risk_approved_count < self.settings.controlled_paper_preflight_min_risk_approved_count:
            return "OBSERVE_ONLY"
        if any(not check.passed for check in checks):
            return "NOT_READY"
        return "READY_FOR_OPERATOR_CONFIG_REVIEW"

    def _disabled_report(self) -> dict:
        """Return disabled report."""
        return ControlledPaperPreflightReport(
            preflight_status="DISABLED",
            activation_eligible=False,
            config_change_required=True,
            controlled_paper_enabled_now=self.settings.controlled_paper_observation_enabled,
            buys_allowed_now=self.settings.controlled_paper_observation_allow_buys,
            sells_allowed_now=self.settings.controlled_paper_observation_allow_sells,
            paper_trade_execution_allowed_now=False,
            live_review_allowed=False,
            audit_passed=False,
            review_clean=False,
            fresh_validation_passed=False,
            current_risk_clean=False,
            legacy_warnings_present=False,
            approval_gate_status="UNKNOWN",
            paper_trade_readiness_status="UNKNOWN",
            completed_runs_analyzed=0,
            observations_analyzed=0,
            strong_buy_count=0,
            risk_approved_count=0,
            recommended_next_actions=["Enable preflight in config only in a future planning phase."],
        ).to_dict()

    def _actions(self, status: str) -> list[str]:
        """Return next actions."""
        if status == "READY_FOR_OPERATOR_CONFIG_REVIEW":
            return ["Review activation plan manually; do not enable paper trades in this phase."]
        if status == "OBSERVE_ONLY":
            return ["Continue observation-only mode until STRONG_BUY and risk-approved evidence exists."]
        if status == "BLOCKED":
            return ["Resolve preflight blockers before considering controlled paper activation."]
        return ["Continue collecting fresh observation data."]

    def _final_recommendation(self, report: dict) -> str:
        """Return final package recommendation."""
        if report.get("preflight_status") == "READY_FOR_OPERATOR_CONFIG_REVIEW":
            return "Eligible for manual operator config review only; no trades are enabled."
        if report.get("preflight_status") == "OBSERVE_ONLY":
            return "Remain observe-only and collect more qualifying signals."
        return "Do not activate controlled paper observation."
