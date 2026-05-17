"""Paper-trade observation readiness gate."""

from __future__ import annotations

from app.calibration.strategy_decision_gate import StrategyDecisionGate
from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_metrics import flatten_results
from app.observation.paper_trade_readiness_models import PaperTradeReadinessCheck, PaperTradeReadinessReport
from app.risk.risk_record_hygiene import RiskRecordHygiene


class PaperTradeReadinessService:
    """Validate readiness for a future paper-trade observation phase."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        safety_audit: SafetyAudit | None = None,
        risk_hygiene: RiskRecordHygiene | None = None,
        decision_gate: StrategyDecisionGate | None = None,
        early_recovery: EarlyRecoveryWatchlistService | None = None,
    ) -> None:
        """Initialize readiness service."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.risk_hygiene = risk_hygiene or RiskRecordHygiene()
        self.decision_gate = decision_gate or StrategyDecisionGate(settings=self.settings, safety_audit=self.safety_audit)
        self.early_recovery = early_recovery or EarlyRecoveryWatchlistService(settings=self.settings)

    def check(self, runs: list[dict] | None = None, risk_records: list[dict] | None = None) -> dict:
        """Return paper-trade observation readiness."""
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        completed = [run for run in runs if run.get("status") == "completed"]
        results = flatten_results(completed)
        safety = self.safety_audit.run().to_dict()
        decision = self.decision_gate.evaluate(completed, safety_report=safety).to_dict()
        hygiene = self.risk_hygiene.summary(records=risk_records)
        recent_cleanliness = self._recent_cleanliness(hygiene, risk_records)
        legacy_aware = self._legacy_aware_readiness(recent_cleanliness, risk_records)
        early = EarlyRecoveryWatchlistService(settings=self.settings, runs=completed).get_report()
        strong_buy_count = sum(1 for result in results if (result.get("signal") or {}).get("category") == "STRONG_BUY")
        risk_approved_count = sum(1 for result in results if (result.get("risk_decision") or {}).get("approved"))
        checks = [
            self._check("safety_audit", bool(safety.get("passed")), "Safety audit must pass", safety),
            self._check("live_trading_locked", bool(safety.get("live_trading_locked")), "Live trading must remain locked", safety),
            self._check("add_order_absent", bool(safety.get("no_add_order_detected")), "Kraken live order endpoint token must be absent", safety),
            self._check("completed_runs", len(completed) >= self.settings.paper_trade_observation_min_completed_runs, "Enough completed observation runs required", {"completed_runs": len(completed)}),
            self._check("observations", len(results) >= self.settings.paper_trade_observation_min_observations, "Enough observations required", {"observations": len(results)}),
            self._check("strong_buy_signals", strong_buy_count > 0 or not self.settings.paper_trade_observation_require_strong_buy, "STRONG_BUY observations required for paper-trade review", {"strong_buy_count": strong_buy_count}),
            self._check("risk_approvals", risk_approved_count > 0 or not self.settings.paper_trade_observation_require_risk_approval, "Risk-approved observations required for paper-trade review", {"risk_approved_count": risk_approved_count}),
            self._check("risk_record_hygiene", recent_cleanliness.get("blocking_inconsistency_count", hygiene["inconsistency_count"]) <= self.settings.paper_trade_observation_max_recent_risk_inconsistencies, "Risk records must be internally consistent", {"hygiene": hygiene, "recent_cleanliness": recent_cleanliness, "legacy_aware_readiness": legacy_aware}),
            self._check("early_recovery_observe_only", self._early_recovery_observe_only(early), "Early recovery must remain observe-only", {"early_recovery_count": len(early.get("candidates", []))}),
            self._check("paper_trades_disabled", not self.settings.paper_trade_observation_allow_enable, "Paper trade observation must remain disabled in this phase", {}),
            self._check("operator_approval_required", self.settings.paper_trade_observation_require_operator_approval, "Future paper-trade observation requires operator approval", {}),
        ]
        blockers = [blocker for check in checks for blocker in check.blockers]
        warnings = [warning for check in checks for warning in check.warnings]
        if hygiene["inconsistency_count"]:
            warnings.append("Risk record hygiene requires review before paper-trade observation.")
        if legacy_aware.get("legacy_present"):
            warnings.append("Legacy risk records remain in audit history and are not deleted.")
        report = PaperTradeReadinessReport(
            ready=False,
            decision="BLOCKED" if self._hard_blocked(checks) else ("OBSERVE_ONLY" if early.get("candidates") else "NOT_READY"),
            confidence="LOW" if len(results) < self.settings.paper_trade_observation_min_observations else "MEDIUM",
            completed_runs_analyzed=len(completed),
            observations_analyzed=len(results),
            strong_buy_count=strong_buy_count,
            risk_approved_count=risk_approved_count,
            early_recovery_count=len(early.get("candidates", [])),
            risk_record_inconsistencies=hygiene["inconsistency_count"],
            safety_audit_passed=bool(safety.get("passed")),
            live_trading_locked=bool(safety.get("live_trading_locked")),
            add_order_absent=bool(safety.get("no_add_order_detected")),
            paper_trade_observation_allowed_now=False,
            operator_approval_required=self.settings.paper_trade_observation_require_operator_approval,
            checks=[check.to_dict() for check in checks],
            warnings=list(dict.fromkeys(warnings)),
            blockers=list(dict.fromkeys(blockers)),
            recommended_next_actions=self._actions(strong_buy_count, risk_approved_count, hygiene["inconsistency_count"]),
        )
        return report.to_dict()

    def _check(self, name: str, passed: bool, message: str, metadata: dict) -> PaperTradeReadinessCheck:
        """Build a readiness check."""
        return PaperTradeReadinessCheck(
            name=name,
            passed=passed,
            status="PASS" if passed else "BLOCKED",
            message=message,
            blockers=[] if passed else [message],
            metadata=metadata,
        )

    def _early_recovery_observe_only(self, report: dict) -> bool:
        """Return whether all early recovery candidates are observe-only."""
        return all(not item.get("trade_allowed") and not item.get("paper_trade_allowed") and not item.get("live_trade_allowed") and item.get("action") == "OBSERVE_ONLY" for item in report.get("candidates", []))

    def _recent_cleanliness(self, hygiene: dict, risk_records: list[dict] | None) -> dict:
        """Return recent risk cleanliness while tolerating older test doubles."""
        if risk_records is None and hasattr(self.risk_hygiene, "validate_recent_records_only"):
            return self.risk_hygiene.validate_recent_records_only()
        if risk_records is not None and hasattr(self.risk_hygiene, "validate_recent_records_only_from_records"):
            return self.risk_hygiene.validate_recent_records_only_from_records(risk_records)
        return {
            "passed": bool(hygiene.get("passed")),
            "blocking_inconsistency_count": hygiene.get("inconsistency_count", 0),
            "source": "crypto_hunter_risk_recent_cleanliness_v1",
        }

    def _legacy_aware_readiness(self, recent_cleanliness: dict, risk_records: list[dict] | None) -> dict:
        """Return legacy-aware readiness while tolerating older test doubles."""
        if risk_records is None and hasattr(self.risk_hygiene, "legacy_aware_readiness"):
            return self.risk_hygiene.legacy_aware_readiness()
        if risk_records is not None and hasattr(self.risk_hygiene, "legacy_aware_readiness"):
            return self.risk_hygiene.legacy_aware_readiness(records=risk_records)
        return {
            "passed": bool(recent_cleanliness.get("passed")),
            "current_clean": recent_cleanliness.get("current_inconsistency_count", 0) == 0,
            "legacy_present": recent_cleanliness.get("legacy_inconsistency_count", 0) > 0,
            "legacy_warn_only": recent_cleanliness.get("legacy_warn_only", False),
            "source": "crypto_hunter_legacy_aware_risk_readiness_v1",
        }

    def _hard_blocked(self, checks: list[PaperTradeReadinessCheck]) -> bool:
        """Return whether safety/hygiene hard blockers exist."""
        hard = {"safety_audit", "live_trading_locked", "add_order_absent", "risk_record_hygiene", "paper_trades_disabled"}
        return any(check.name in hard and not check.passed for check in checks)

    def _actions(self, strong_buy_count: int, risk_approved_count: int, inconsistency_count: int) -> list[str]:
        """Return recommended next actions."""
        actions = ["Keep early recovery candidates observe-only.", "Continue persisted observation windows."]
        if strong_buy_count == 0:
            actions.append("Wait for repeated STRONG_BUY observations before paper-trade observation review.")
        if risk_approved_count == 0:
            actions.append("Wait for clean risk-approved paper observations before any paper-trade observation phase.")
        if inconsistency_count:
            actions.append("Review risk record hygiene inconsistencies before future paper-trade observation.")
        actions.append("Operator approval is required before any future paper-trade observation enablement.")
        return actions
