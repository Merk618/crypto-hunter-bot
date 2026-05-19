"""Local operator runbook and one-command health check."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from app.audit.final_safety_review import FinalSafetyReview
from app.audit.standalone_readiness_audit import StandaloneReadinessAudit
from app.audit.v1_completion_checklist import V1CompletionChecklistService
from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.observation.controlled_paper_audit import ControlledPaperAuditService
from app.observation.controlled_paper_observation import ControlledPaperObservationService
from app.observation.signal_quality_review import SignalQualityReviewService
from app.observation.strategy_review_checkpoint import StrategyReviewCheckpointService


@dataclass
class LocalRunbook:
    """Local operator runbook."""

    title: str
    sections: list[dict]
    commands: list[dict]
    troubleshooting: list[str]
    warnings: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_local_operator_runbook_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class OneCommandHealthCheckReport:
    """One-command local health check."""

    passed: bool
    status: str
    checks: list[dict]
    warnings: list[str]
    blockers: list[str]
    recommended_next_actions: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_one_command_health_check_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class LocalOperatorRunbookService:
    """Build local runbook and health check responses."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize local runbook dependencies."""
        self.settings = settings or get_settings()

    def runbook(self) -> dict:
        """Return local runbook."""
        commands = self._commands()
        return LocalRunbook(
            title="Crypto Hunter v1 Local Operator Runbook",
            sections=[
                {"title": "Start Backend", "steps": ["Open PowerShell in the repo root.", "Run the backend start command.", "Leave the terminal open while using the API."]},
                {"title": "Verify Safety", "steps": ["Run pytest.", "Run the one-command health check.", "Review safety audit and final safety review endpoints."]},
                {"title": "Review Strategy", "steps": ["Review signal quality.", "Review strategy checkpoint.", "Review extended observation plan."]},
                {"title": "Confirm Disabled Trading", "steps": ["Check controlled paper status.", "Check controlled paper audit.", "Confirm live trading remains locked."]},
                {"title": "Stop Backend", "steps": ["Return to the uvicorn terminal.", "Press Ctrl+C."]},
            ],
            commands=commands,
            troubleshooting=[
                "If the backend is not reachable, start uvicorn and retry.",
                "If safety audit fails, do not continue to observation review until blockers are fixed.",
                "If Kraken public data is unavailable, use validation endpoints to distinguish network failure from app failure.",
            ],
            warnings=["Runbook commands do not place real orders.", "Phase 42 does not enable paper or live trading."],
        ).to_dict()

    def startup_guide(self) -> dict:
        """Return compact startup guide."""
        return {
            "title": "Crypto Hunter v1 Startup Guide",
            "steps": [
                "Run tests with .\\.venv\\Scripts\\python.exe -m pytest",
                "Start backend with .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload",
                "Run scripts\\health_check_phase42.py",
                "Review /audit/standalone-readiness and /strategy/review-checkpoint",
            ],
            "stop_backend": "Press Ctrl+C in the uvicorn terminal.",
            "source": "crypto_hunter_v1_startup_guide_v1",
        }

    def local_smoke_test(self) -> dict:
        """Return lightweight smoke-test summary without network requirements."""
        health = self.one_command_health_check()
        return {
            "passed": bool(health.get("passed")),
            "checks": health.get("checks", []),
            "warnings": ["Local smoke test is read-only and does not place trades."],
            "source": "crypto_hunter_local_v1_smoke_test_v1",
        }

    def one_command_health_check(self) -> dict:
        """Run local health checks using internal services."""
        checks = []
        checks.append(self._check("backend_imports", True, "Backend modules imported."))
        checks.append(self._check("config_loads", isinstance(self.settings, Settings), "Config loads."))
        safety = SafetyAudit(settings=self.settings).run().to_dict()
        final = FinalSafetyReview(settings=self.settings).review(safety_report=safety)
        readiness = StandaloneReadinessAudit(settings=self.settings).audit(safety_report=safety)
        checklist = V1CompletionChecklistService(settings=self.settings).build()
        strategy = StrategyReviewCheckpointService(settings=self.settings).checkpoint()
        signal = SignalQualityReviewService(settings=self.settings).review()
        controlled_status = ControlledPaperObservationService(settings=self.settings).status()
        controlled_audit = ControlledPaperAuditService(settings=self.settings).audit()
        checks.extend(
            [
                self._check("safety_audit", bool(safety.get("passed")), "Safety audit passes.", safety),
                self._check("final_safety_review", bool(final.get("passed")), "Final safety review passes.", final),
                self._check("standalone_readiness", readiness.get("readiness_status") in {"READY_FOR_FINAL_RUNBOOK", "READY_FOR_V1_FREEZE"}, "Standalone readiness endpoint works.", readiness),
                self._check("v1_checklist", "items" in checklist, "V1 checklist endpoint works.", checklist),
                self._check("strategy_checkpoint", "decision" in strategy, "Strategy checkpoint endpoint works.", strategy),
                self._check("signal_quality", "observations_analyzed" in signal, "Signal quality endpoint works.", signal),
                self._check("controlled_paper_status", controlled_status.get("enabled") is False, "Controlled paper status is disabled.", controlled_status),
                self._check("controlled_paper_audit", bool(controlled_audit.get("passed")), "Controlled paper audit passes.", controlled_audit),
                self._check("forbidden_live_order_absent", bool(safety.get("no_add_order_detected")), "Forbidden live order token is absent.", safety),
                self._check("live_trading_locked", bool(safety.get("live_trading_locked")), "Live trading is locked.", safety),
                self._check("paper_trading_disabled", self._paper_disabled(), "Paper-trade observation is disabled.", {}),
                self._check("secrets_not_exposed", bool(safety.get("secrets_not_exposed")), "Secrets are not exposed.", safety),
            ]
        )
        blockers = [check["message"] for check in checks if not check["passed"]]
        report = OneCommandHealthCheckReport(
            passed=not blockers,
            status="PASS" if not blockers else "FAIL",
            checks=checks,
            warnings=["Health check is read-only and does not enable trading."],
            blockers=blockers,
            recommended_next_actions=["Proceed to Phase 43 v1 freeze package." if not blockers else "Resolve health check blockers before v1 freeze."],
        )
        return report.to_dict()

    def _commands(self) -> list[dict]:
        """Return PowerShell runbook commands."""
        return [
            {"label": "Run tests", "command": r".\.venv\Scripts\python.exe -m pytest"},
            {"label": "Start backend", "command": r".\.venv\Scripts\python.exe -m uvicorn app.main:app --reload"},
            {"label": "Run health check", "command": r".\.venv\Scripts\python.exe scripts\health_check_phase42.py"},
            {"label": "Safety audit", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/system/safety-audit"'},
            {"label": "Strategy review", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/strategy/review-checkpoint"'},
            {"label": "Observation plan", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/strategy/extended-observation-plan"'},
            {"label": "Controlled paper disabled", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/status"'},
            {"label": "Stop backend", "command": "Ctrl+C in the uvicorn terminal"},
        ]

    def _check(self, name: str, passed: bool, message: str, metadata: dict | None = None) -> dict:
        """Build one health check item."""
        return {"name": name, "passed": bool(passed), "status": "PASS" if passed else "FAIL", "message": message, "metadata": metadata or {}}

    def _paper_disabled(self) -> bool:
        """Return whether paper-trade observation is disabled."""
        return (
            not self.settings.paper_trade_observation_enabled
            and not self.settings.paper_trade_observation_allow_enable
            and not self.settings.controlled_paper_observation_enabled
            and not self.settings.controlled_paper_observation_allow_buys
        )
