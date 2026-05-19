"""Signal quality review models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class SignalQualitySymbolSummary:
    """Per-symbol observation signal quality summary."""

    symbol: str
    observations: int
    average_score: float | None
    latest_score: float | None
    max_score: float | None
    min_score: float | None
    latest_category: str
    strongest_category: str
    strong_buy_count: int
    buy_watch_count: int
    neutral_count: int
    weak_count: int
    risk_approved_count: int
    dominant_blockers: list[dict] = field(default_factory=list)
    dominant_warnings: list[dict] = field(default_factory=list)
    early_recovery_candidate: bool = False
    score_trend: str = "INSUFFICIENT_DATA"
    near_buy_watch_count: int = 0
    near_strong_buy_count: int = 0
    recommendation: str = "CONTINUE_OBSERVATION_ONLY"
    source: str = "crypto_hunter_signal_quality_symbol_summary_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class SignalQualityReviewReport:
    """Signal quality review report."""

    observations_analyzed: int
    completed_runs_analyzed: int
    symbols_analyzed: int
    average_score: float | None
    max_score: float | None
    strong_buy_count: int
    buy_watch_count: int
    neutral_count: int
    weak_count: int
    risk_approved_count: int
    early_recovery_count: int
    near_buy_watch_count: int
    near_strong_buy_count: int
    dominant_blockers: list[dict] = field(default_factory=list)
    blocker_distribution: dict[str, int] = field(default_factory=dict)
    warning_distribution: dict[str, int] = field(default_factory=dict)
    symbol_summaries: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    threshold_change_recommended: bool = False
    paper_trade_observation_recommended: bool = False
    live_review_recommended: bool = False
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_signal_quality_review_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ObservationContinuationPlan:
    """Observation continuation plan."""

    decision: str
    confidence: str
    continue_observation_only: bool
    additional_runs_recommended: int
    additional_observations_recommended: int
    threshold_changes_allowed: bool = False
    paper_trades_allowed: bool = False
    live_review_allowed: bool = False
    reasons: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_observation_continuation_plan_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
