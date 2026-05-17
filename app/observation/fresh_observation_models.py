"""Fresh observation validation models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class FreshObservationRunSummary:
    """One fresh observation run summary."""

    run_id: str | None
    status: str
    started_at: str | None
    completed_at: str | None
    symbols_processed: int
    signals_generated: int
    risk_decisions_generated: int
    paper_trades_created: int
    clean_risk_records: int
    current_inconsistencies: int
    legacy_warnings: int
    source: str = "crypto_hunter_fresh_observation_run_summary_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class FreshObservationValidationReport:
    """Fresh observation validation report."""

    passed: bool
    status: str
    completed_runs_checked: int
    observation_results_checked: int
    persisted_results_found: bool
    current_clean: bool
    current_inconsistency_count: int
    legacy_inconsistency_count: int
    legacy_warn_only: bool
    clean_rejected_count: int
    clean_approved_count: int
    strong_buy_count: int
    risk_approved_count: int
    paper_trades_created: int
    paper_trade_observation_allowed_now: bool = False
    live_review_allowed: bool = False
    run_summaries: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_fresh_observation_validation_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
