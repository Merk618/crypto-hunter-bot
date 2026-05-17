"""Validate fresh persisted observation windows after risk hygiene fixes."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.observation.fresh_observation_models import FreshObservationRunSummary, FreshObservationValidationReport
from app.observation.observation_hydration import ObservationHydrationService
from app.risk.risk_record_hygiene import RiskRecordHygiene


class FreshObservationValidator:
    """Read-only validator for fresh post-Phase31/32 observation windows."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        hygiene: RiskRecordHygiene | None = None,
    ) -> None:
        """Initialize validator."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.hygiene = hygiene or RiskRecordHygiene(settings=self.settings)

    def validate(self, runs: list[dict] | None = None) -> dict:
        """Validate recent fresh completed observation runs."""
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit, include_refused=not self.settings.fresh_observation_require_completed_runs_only)
        completed = [run for run in runs if run.get("status") == "completed"]
        selected = completed if self.settings.fresh_observation_require_completed_runs_only else runs
        results = [result for run in selected for result in run.get("results", [])]
        risk_records = [self._risk_record(result, idx) for idx, result in enumerate(results) if result.get("risk_decision")]
        classified = [self.hygiene.classify_risk_record(record) for record in risk_records]
        clean_rejected = [item for item in classified if item.get("classification") == "CLEAN_REJECTED_RECORD"]
        clean_approved = [item for item in classified if item.get("classification") == "CLEAN_APPROVED_RECORD"]
        current = [item for item in classified if item.get("classification") == "CURRENT_INCONSISTENT_REJECTED_RECORD"]
        legacy = [item for item in classified if item.get("classification") == "LEGACY_INCONSISTENT_REJECTED_RECORD"]
        strong_buy_count = sum(1 for result in results if (result.get("signal") or {}).get("category") == "STRONG_BUY")
        risk_approved_count = sum(1 for result in results if (result.get("risk_decision") or {}).get("approved"))
        paper_trades_created = sum(1 for result in results if result.get("paper_trade_result"))
        warnings: list[str] = []
        blockers: list[str] = []
        if legacy:
            warnings.append("Legacy risk records remain in audit history and are not deleted.")
        if paper_trades_created:
            warnings.append("Paper trades were found in observation history; Phase 33 does not enable them.")
        if len(completed) < self.settings.fresh_observation_min_completed_runs:
            blockers.append("Fresh validation needs more completed observation runs.")
        if len(results) < self.settings.fresh_observation_min_results:
            blockers.append("Fresh validation needs more observation results.")
        if self.settings.fresh_observation_require_persisted_results and not results:
            blockers.append("No persisted observation results were found.")
        if len(current) > self.settings.fresh_observation_max_current_inconsistencies:
            blockers.append("Current inconsistent rejected risk records detected.")
        status = self._status(blockers, completed, results, current)
        report = FreshObservationValidationReport(
            passed=status == "PASSED",
            status=status,
            completed_runs_checked=len(completed),
            observation_results_checked=len(results),
            persisted_results_found=bool(results),
            current_clean=not current,
            current_inconsistency_count=len(current),
            legacy_inconsistency_count=len(legacy),
            legacy_warn_only=self.settings.fresh_observation_allow_legacy_warnings,
            clean_rejected_count=len(clean_rejected),
            clean_approved_count=len(clean_approved),
            strong_buy_count=strong_buy_count,
            risk_approved_count=risk_approved_count,
            paper_trades_created=paper_trades_created,
            paper_trade_observation_allowed_now=False,
            live_review_allowed=False,
            run_summaries=[self._summarize_run(run) for run in selected],
            warnings=list(dict.fromkeys(warnings)),
            blockers=list(dict.fromkeys(blockers)),
            recommended_next_actions=self._actions(status, strong_buy_count, risk_approved_count),
        )
        return report.to_dict()

    def run_summaries(self, runs: list[dict] | None = None) -> dict:
        """Return run-level fresh validation summaries."""
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        completed = [run for run in runs if run.get("status") == "completed"]
        summaries = [self._summarize_run(run).to_dict() for run in completed]
        return {
            "runs": summaries,
            "count": len(summaries),
            "source": "crypto_hunter_fresh_observation_run_summaries_v1",
        }

    def readiness(self, runs: list[dict] | None = None) -> dict:
        """Return compact fresh validation readiness."""
        report = self.validate(runs=runs)
        return {
            "ready": bool(report.get("passed")),
            "status": report.get("status"),
            "current_clean": report.get("current_clean"),
            "legacy_warn_only": report.get("legacy_warn_only"),
            "paper_trade_observation_allowed_now": False,
            "live_review_allowed": False,
            "warnings": report.get("warnings", []),
            "blockers": report.get("blockers", []),
            "source": "crypto_hunter_fresh_observation_readiness_v1",
        }

    def _risk_record(self, result: dict, idx: int) -> dict:
        """Build hygiene-compatible risk record from observation result."""
        risk = dict(result.get("risk_decision") or {})
        risk.setdefault("id", idx + 1)
        risk.setdefault("symbol", result.get("symbol") or risk.get("symbol"))
        risk.setdefault("side", risk.get("side") or "buy")
        return risk

    def _summarize_run(self, run: dict) -> FreshObservationRunSummary:
        """Summarize one observation run."""
        results = run.get("results", [])
        risk_records = [self._risk_record(result, idx) for idx, result in enumerate(results) if result.get("risk_decision")]
        classified = [self.hygiene.classify_risk_record(record) for record in risk_records]
        current = [item for item in classified if item.get("classification") == "CURRENT_INCONSISTENT_REJECTED_RECORD"]
        legacy = [item for item in classified if item.get("classification") == "LEGACY_INCONSISTENT_REJECTED_RECORD"]
        clean = [item for item in classified if item.get("classification") in {"CLEAN_REJECTED_RECORD", "CLEAN_APPROVED_RECORD"}]
        return FreshObservationRunSummary(
            run_id=run.get("run_id"),
            status=str(run.get("status", "unknown")),
            started_at=run.get("started_at"),
            completed_at=run.get("completed_at"),
            symbols_processed=int(run.get("symbols_processed") or len({result.get("symbol") for result in results if result.get("symbol")})),
            signals_generated=int(run.get("signals_generated") or sum(1 for result in results if result.get("signal"))),
            risk_decisions_generated=int(run.get("risk_decisions_generated") or len(risk_records)),
            paper_trades_created=int(run.get("paper_trades_created") or sum(1 for result in results if result.get("paper_trade_result"))),
            clean_risk_records=len(clean),
            current_inconsistencies=len(current),
            legacy_warnings=len(legacy),
        )

    def _status(self, blockers: list[str], completed: list[dict], results: list[dict], current: list[dict]) -> str:
        """Return validation status."""
        if current:
            return "BLOCKED_CURRENT_RISK_INCONSISTENCY"
        if len(completed) < self.settings.fresh_observation_min_completed_runs or len(results) < self.settings.fresh_observation_min_results:
            return "INSUFFICIENT_DATA"
        return "BLOCKED" if blockers else "PASSED"

    def _actions(self, status: str, strong_buy_count: int, risk_approved_count: int) -> list[str]:
        """Return recommended next actions."""
        actions = []
        if status == "INSUFFICIENT_DATA":
            actions.append("Run a fresh observation window with at least two completed runs.")
        if status == "BLOCKED_CURRENT_RISK_INCONSISTENCY":
            actions.append("Investigate current risk persistence before continuing readiness review.")
        if status == "PASSED":
            actions.append("Fresh risk persistence looks clean; continue observation-only validation.")
        if strong_buy_count == 0:
            actions.append("Paper-trade readiness still needs repeated STRONG_BUY observations.")
        if risk_approved_count == 0:
            actions.append("Paper-trade readiness still needs clean risk-approved observations.")
        actions.append("Fresh validation passing does not enable paper or live trading.")
        return list(dict.fromkeys(actions))
