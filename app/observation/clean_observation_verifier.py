"""Verify clean post-remediation observation risk records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.observation.observation_hydration import ObservationHydrationService
from app.risk.risk_record_hygiene import RiskRecordHygiene


@dataclass
class CleanObservationVerificationReport:
    """Clean observation verification report."""

    passed: bool
    completed_runs_checked: int
    observation_results_checked: int
    current_risk_records_checked: int
    current_inconsistency_count: int
    legacy_inconsistency_count: int
    clean_rejected_count: int
    clean_approved_count: int
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_clean_observation_verification_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class CleanObservationVerifier:
    """Verify that recent completed observations produce clean risk decisions."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        hygiene: RiskRecordHygiene | None = None,
    ) -> None:
        """Initialize verifier."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.hygiene = hygiene or RiskRecordHygiene(settings=self.settings)

    def verify(self, runs: list[dict] | None = None) -> dict:
        """Verify recent completed observation runs and risk decisions."""
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        completed = [run for run in runs if run.get("status") == "completed"]
        results = [result for run in completed for result in run.get("results", [])]
        risk_records = [self._risk_record_from_result(result, index) for index, result in enumerate(results) if result.get("risk_decision")]
        classified = [self.hygiene.classify_risk_record(record) for record in risk_records]
        current_inconsistent = [item for item in classified if item.get("classification") == "CURRENT_INCONSISTENT_REJECTED_RECORD"]
        legacy_inconsistent = [item for item in classified if item.get("classification") == "LEGACY_INCONSISTENT_REJECTED_RECORD"]
        clean_rejected = [item for item in classified if item.get("classification") == "CLEAN_REJECTED_RECORD"]
        clean_approved = [item for item in classified if item.get("classification") == "CLEAN_APPROVED_RECORD"]
        warnings: list[str] = []
        blockers: list[str] = []
        if len(completed) < self.settings.clean_observation_verification_min_runs:
            blockers.append("Not enough completed observation runs to verify clean post-Phase31 behavior.")
        if len(results) < self.settings.clean_observation_verification_min_results:
            blockers.append("Not enough observation results to verify clean post-Phase31 behavior.")
        if legacy_inconsistent:
            warnings.append("Legacy risk records remain in audit history and are not deleted.")
        if current_inconsistent:
            blockers.append("Current inconsistent rejected risk records detected.")
        passed = not blockers
        report = CleanObservationVerificationReport(
            passed=passed,
            completed_runs_checked=len(completed),
            observation_results_checked=len(results),
            current_risk_records_checked=len(risk_records),
            current_inconsistency_count=len(current_inconsistent),
            legacy_inconsistency_count=len(legacy_inconsistent),
            clean_rejected_count=len(clean_rejected),
            clean_approved_count=len(clean_approved),
            warnings=list(dict.fromkeys(warnings)),
            blockers=list(dict.fromkeys(blockers)),
            recommended_next_actions=self._actions(passed, current_inconsistent, legacy_inconsistent),
        )
        return report.to_dict()

    def _risk_record_from_result(self, result: dict, index: int) -> dict:
        """Convert an observation result risk decision to hygiene-compatible shape."""
        risk = dict(result.get("risk_decision") or {})
        risk.setdefault("id", index + 1)
        risk.setdefault("symbol", result.get("symbol") or risk.get("symbol"))
        risk.setdefault("side", risk.get("side") or "buy")
        return risk

    def _actions(self, passed: bool, current: list[dict], legacy: list[dict]) -> list[str]:
        """Return recommended next actions."""
        actions = []
        if current:
            actions.append("Investigate current risk persistence before any paper-trade observation review.")
        if legacy:
            actions.append("Keep legacy inconsistent records visible as audit warnings.")
        if passed:
            actions.append("Continue observation windows; paper trades remain disabled until separate readiness criteria pass.")
        else:
            actions.append("Collect additional clean post-Phase31 observations before paper-trade observation review.")
        return actions
