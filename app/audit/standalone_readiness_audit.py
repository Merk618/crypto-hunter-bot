"""Final standalone readiness audit."""

from __future__ import annotations

from pathlib import Path

from app.audit.final_safety_review import FinalSafetyReview
from app.audit.standalone_readiness_models import StandaloneReadinessAuditReport
from app.audit.v1_completion_checklist import V1CompletionChecklistService
from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit


class StandaloneReadinessAudit:
    """Audit whether Crypto Hunter is ready for final standalone runbook work."""

    def __init__(
        self,
        settings: Settings | None = None,
        safety_audit: SafetyAudit | None = None,
        final_safety: FinalSafetyReview | None = None,
        checklist: V1CompletionChecklistService | None = None,
        root: Path | None = None,
    ) -> None:
        """Initialize standalone readiness audit."""
        self.settings = settings or get_settings()
        self.root = root or Path(__file__).resolve().parents[2]
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings, root=self.root)
        self.final_safety = final_safety or FinalSafetyReview(settings=self.settings, safety_audit=self.safety_audit, root=self.root)
        self.checklist = checklist or V1CompletionChecklistService(settings=self.settings, root=self.root)

    def audit(self, safety_report: dict | None = None, route_text: str | None = None) -> dict:
        """Return standalone readiness audit."""
        safety = safety_report or self.safety_audit.run().to_dict()
        final = self.final_safety.review(safety_report=safety, route_text=route_text)
        routes = route_text if route_text is not None else self._read_file("app/api/routes.py")
        checks = self._checks(safety, final, routes)
        blockers = [check["message"] for check in checks if not check["passed"] and check.get("blocking")]
        checklist = self.checklist.build()
        if not self.settings.standalone_readiness_audit_enabled:
            blockers.append("Standalone readiness audit is disabled.")
        status = self._status(blockers, checklist)
        report = StandaloneReadinessAuditReport(
            ready_for_v1_freeze=False,
            readiness_status=status,
            safety_audit_passed=bool(safety.get("passed")),
            live_trading_locked=bool(safety.get("live_trading_locked")),
            add_order_absent=bool(safety.get("no_add_order_detected")),
            real_execution_absent=bool(final.get("private_order_methods_absent")),
            paper_trading_disabled=not self.settings.paper_trade_observation_enabled and not self.settings.paper_trade_observation_allow_enable,
            controlled_paper_disabled=not self.settings.controlled_paper_observation_enabled and not self.settings.controlled_paper_observation_allow_buys,
            observation_persistence_available=self._exists("app/observation/observation_persistence.py"),
            strategy_checkpoint_available=self._exists("app/observation/strategy_review_checkpoint.py"),
            reporting_available="/reports/system-health" in routes,
            operator_layer_available="/operator/status" in routes,
            docs_available=self._exists("docs/STRATEGY_REVIEW_CHECKPOINT_PHASE40.md"),
            test_suite_expected_minimum=697,
            warnings=self._warnings(status),
            blockers=list(dict.fromkeys(blockers)),
            checks=checks,
            recommended_next_actions=self._actions(status),
        )
        return report.to_dict()

    def _checks(self, safety: dict, final: dict, routes: str) -> list[dict]:
        """Build readiness checks."""
        return [
            self._check("safety_audit", bool(safety.get("passed")) or not self.settings.standalone_require_safety_audit, "Safety audit must pass."),
            self._check("live_locked", bool(safety.get("live_trading_locked")) or not self.settings.standalone_require_live_locked, "Live trading must remain locked."),
            self._check("forbidden_live_order_absent", bool(safety.get("no_add_order_detected")) or not self.settings.standalone_require_addorder_absent, "Forbidden live order token must be absent."),
            self._check("real_execution_absent", bool(final.get("private_order_methods_absent")) or not self.settings.standalone_require_no_real_execution_routes, "Real execution routes must be absent."),
            self._check("observation_persistence", self._exists("app/observation/observation_persistence.py") or not self.settings.standalone_require_observation_persistence, "Observation persistence must exist."),
            self._check("operator_endpoints", "/operator/status" in routes or not self.settings.standalone_require_operator_endpoints, "Operator endpoints must exist."),
            self._check("reporting_endpoints", "/reports/system-health" in routes or not self.settings.standalone_require_reporting_endpoints, "Reporting endpoints must exist."),
            self._check("docs", self._exists("README.md") and self._exists("docs/STRATEGY_REVIEW_CHECKPOINT_PHASE40.md") or not self.settings.standalone_require_docs, "Docs must be available."),
            self._check("paper_disabled", not self.settings.standalone_allow_paper_trading and not self.settings.controlled_paper_observation_enabled, "Paper trading must remain disabled."),
            self._check("live_disabled", not self.settings.standalone_allow_live_trading and not self.settings.enable_live_trading, "Live trading must remain disabled."),
        ]

    def _check(self, name: str, passed: bool, message: str, blocking: bool = True) -> dict:
        """Build one check."""
        return {"name": name, "passed": bool(passed), "status": "PASS" if passed else "BLOCKED", "message": message, "blocking": blocking}

    def _status(self, blockers: list[str], checklist: dict) -> str:
        """Return readiness status."""
        if blockers:
            return "BLOCKED"
        if checklist.get("complete"):
            return "READY_FOR_V1_FREEZE"
        return "READY_FOR_FINAL_RUNBOOK"

    def _warnings(self, status: str) -> list[str]:
        """Return warnings."""
        warnings = ["Crypto Hunter v1 is observation/safety-first and does not enable live trading."]
        if status == "READY_FOR_FINAL_RUNBOOK":
            warnings.append("Final runbook and freeze package are still needed before v1 freeze.")
        return warnings

    def _actions(self, status: str) -> list[str]:
        """Return recommended actions."""
        if status == "BLOCKED":
            return ["Resolve standalone readiness blockers before final runbook work."]
        if status == "READY_FOR_FINAL_RUNBOOK":
            return ["Phase 42: create local operator runbook and one-command health check.", "Phase 43: prepare v1 freeze and handoff package."]
        return ["Prepare v1 freeze package."]

    def _exists(self, rel: str) -> bool:
        """Return whether repo file exists."""
        return (self.root / rel).exists()

    def _read_file(self, rel: str) -> str:
        """Read repo file."""
        path = self.root / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
