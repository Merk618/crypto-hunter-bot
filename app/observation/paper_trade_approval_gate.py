"""Read-only paper-trade observation approval gate."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.observation.clean_observation_verifier import CleanObservationVerifier
from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.observation.fresh_observation_validator import FreshObservationValidator
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_metrics import flatten_results
from app.observation.paper_trade_approval_models import PaperTradeApprovalCheck, PaperTradeApprovalReport
from app.observation.paper_trade_readiness import PaperTradeReadinessService
from app.risk.risk_record_hygiene import RiskRecordHygiene


class PaperTradeApprovalGate:
    """Build a read-only operator approval package for future paper-trade observation."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        safety_audit: SafetyAudit | None = None,
        fresh_validator: FreshObservationValidator | None = None,
        clean_verifier: CleanObservationVerifier | None = None,
        risk_hygiene: RiskRecordHygiene | None = None,
        readiness: PaperTradeReadinessService | None = None,
        early_recovery: EarlyRecoveryWatchlistService | None = None,
    ) -> None:
        """Initialize gate dependencies."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.risk_hygiene = risk_hygiene or RiskRecordHygiene(settings=self.settings)
        self.fresh_validator = fresh_validator or FreshObservationValidator(settings=self.settings, hydration=self.hydration, hygiene=self.risk_hygiene)
        self.clean_verifier = clean_verifier or CleanObservationVerifier(settings=self.settings, hydration=self.hydration, hygiene=self.risk_hygiene)
        self.readiness = readiness or PaperTradeReadinessService(settings=self.settings, hydration=self.hydration, safety_audit=self.safety_audit, risk_hygiene=self.risk_hygiene)
        self.early_recovery = early_recovery or EarlyRecoveryWatchlistService(settings=self.settings, hydration=self.hydration)

    def evaluate(self, runs: list[dict] | None = None, risk_records: list[dict] | None = None, safety_report: dict | None = None, fresh_report: dict | None = None) -> dict:
        """Evaluate operator review eligibility without enabling trades."""
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        completed = [run for run in runs if run.get("status") == "completed"]
        results = flatten_results(completed)
        safety = safety_report or self.safety_audit.run().to_dict()
        fresh = fresh_report or self.fresh_validator.validate(runs=completed)
        legacy = self.risk_hygiene.legacy_aware_readiness(records=risk_records) if risk_records is not None else self.risk_hygiene.legacy_aware_readiness()
        readiness = self.readiness.check(runs=completed, risk_records=risk_records)
        strong_buy_count = sum(1 for result in results if (result.get("signal") or {}).get("category") == "STRONG_BUY")
        risk_approved_count = sum(1 for result in results if (result.get("risk_decision") or {}).get("approved"))
        checks = [
            self._check("safety_audit", bool(safety.get("passed")), "Safety audit must pass", safety, hard=True),
            self._check("live_trading_locked", bool(safety.get("live_trading_locked")), "Live trading must remain locked", safety, hard=True),
            self._check("live_order_token_absent", bool(safety.get("no_add_order_detected")), "Forbidden live order token must be absent", safety, hard=True),
            self._check("fresh_validation", bool(fresh.get("passed")) or not self.settings.paper_trade_approval_require_fresh_validation, "Fresh observation validation must pass", fresh),
            self._check("current_risk_clean", bool(legacy.get("current_clean")) or not self.settings.paper_trade_approval_require_clean_current_risk, "Current risk hygiene must be clean", legacy, hard=True),
            self._check("completed_runs", len(completed) >= self.settings.paper_trade_approval_min_completed_runs, "Minimum completed observations runs required", {"completed_runs": len(completed)}),
            self._check("observations", len(results) >= self.settings.paper_trade_approval_min_observations, "Minimum observations required", {"observations": len(results)}),
            self._check("strong_buy_count", strong_buy_count >= self.settings.paper_trade_approval_min_strong_buy_count or not self.settings.paper_trade_approval_require_strong_buy, "Minimum STRONG_BUY observations required", {"strong_buy_count": strong_buy_count}),
            self._check("risk_approved_count", risk_approved_count >= self.settings.paper_trade_approval_min_risk_approved_count or not self.settings.paper_trade_approval_require_risk_approved, "Minimum risk-approved observations required", {"risk_approved_count": risk_approved_count}),
            self._check("operator_required", bool(self.settings.paper_trade_approval_require_operator), "Operator approval must be required", {}, hard=True),
            self._check("paper_trade_observation_disabled", not self.settings.paper_trade_observation_allow_enable and not self.settings.paper_trade_observation_enabled, "Paper-trade observation remains disabled in this phase", {}, hard=True),
        ]
        warnings = [warning for check in checks for warning in check.warnings]
        if legacy.get("legacy_present"):
            warnings.append("Legacy risk records remain visible as audit warnings.")
        warnings.append("This is not live trading and does not enable paper-trade execution.")
        blockers = [blocker for check in checks for blocker in check.blockers]
        status = self._status(checks)
        eligible = status == "ELIGIBLE_FOR_OPERATOR_REVIEW"
        report = PaperTradeApprovalReport(
            approval_status=status,
            eligible_for_operator_review=eligible,
            approved_for_paper_trade_observation=False,
            paper_trade_observation_enabled=False,
            completed_runs_analyzed=len(completed),
            observations_analyzed=len(results),
            strong_buy_count=strong_buy_count,
            risk_approved_count=risk_approved_count,
            fresh_validation_passed=bool(fresh.get("passed")),
            current_risk_clean=bool(legacy.get("current_clean")),
            legacy_warnings_present=bool(legacy.get("legacy_present")),
            safety_audit_passed=bool(safety.get("passed")),
            live_trading_locked=bool(safety.get("live_trading_locked")),
            add_order_absent=bool(safety.get("no_add_order_detected")),
            operator_approval_required=self.settings.paper_trade_approval_require_operator,
            checks=[check.to_dict() for check in checks],
            warnings=list(dict.fromkeys(warnings)),
            blockers=list(dict.fromkeys(blockers)),
            recommended_next_actions=self._actions(status, strong_buy_count, risk_approved_count),
        )
        return report.to_dict()

    def checks(self) -> dict:
        """Return approval checks only."""
        report = self.evaluate()
        return {"checks": report["checks"], "approval_status": report["approval_status"], "source": "crypto_hunter_paper_trade_approval_checks_v1"}

    def package(self) -> dict:
        """Return read-only approval review package."""
        runs = self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        approval = self.evaluate(runs=runs)
        return {
            "approval": approval,
            "safety": self.safety_audit.run().to_dict(),
            "fresh_validation": self.fresh_validator.validate(runs=runs),
            "clean_observation_verification": self.clean_verifier.verify(runs=runs),
            "legacy_aware_risk_readiness": self.risk_hygiene.legacy_aware_readiness(),
            "paper_trade_readiness": self.readiness.check(runs=[run for run in runs if run.get("status") == "completed"]),
            "early_recovery": self.early_recovery.get_report(),
            "warning": "This is not live trading and does not enable paper-trade execution.",
            "source": "crypto_hunter_paper_trade_approval_package_v1",
        }

    def _check(self, name: str, passed: bool, message: str, metadata: dict, hard: bool = False) -> PaperTradeApprovalCheck:
        """Build one approval check."""
        return PaperTradeApprovalCheck(
            name=name,
            passed=passed,
            status="PASS" if passed else ("BLOCKED" if hard else "NOT_READY"),
            message=message,
            blockers=[] if passed else [message],
            metadata=metadata,
        )

    def _status(self, checks: list[PaperTradeApprovalCheck]) -> str:
        """Return approval status."""
        if not self.settings.paper_trade_approval_gate_enabled:
            return "DISABLED_BY_CONFIG"
        if any(not check.passed and check.status == "BLOCKED" for check in checks):
            return "BLOCKED"
        if any(not check.passed for check in checks):
            return "NOT_READY"
        if not self.settings.paper_trade_observation_allow_enable and not self.settings.paper_trade_observation_enabled:
            return "ELIGIBLE_FOR_OPERATOR_REVIEW"
        return "APPROVED_BUT_NOT_ENABLED"

    def _actions(self, status: str, strong_buy_count: int, risk_approved_count: int) -> list[str]:
        """Return next actions."""
        actions = []
        if status in {"BLOCKED", "NOT_READY"}:
            actions.append("Continue observation-only mode.")
        if strong_buy_count < self.settings.paper_trade_approval_min_strong_buy_count:
            actions.append("Collect repeated STRONG_BUY observations before operator review.")
        if risk_approved_count < self.settings.paper_trade_approval_min_risk_approved_count:
            actions.append("Collect clean risk-approved observations before operator review.")
        if status == "ELIGIBLE_FOR_OPERATOR_REVIEW":
            actions.append("Operator may review paper-trade observation criteria in a future phase.")
        actions.append("Do not enable paper trades or live trading in this phase.")
        return list(dict.fromkeys(actions))
