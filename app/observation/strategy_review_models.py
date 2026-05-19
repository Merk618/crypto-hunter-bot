"""Strategy review checkpoint models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class StrategyReviewCheckpointReport:
    """Formal strategy review checkpoint."""

    checkpoint_status: str
    decision: str
    confidence: str
    observations_analyzed: int
    completed_runs_analyzed: int
    average_score: float | None
    max_score: float | None
    strong_buy_count: int
    buy_watch_count: int
    neutral_count: int
    weak_count: int
    risk_approved_count: int
    early_recovery_count: int
    dominant_blockers: list[dict] = field(default_factory=list)
    strongest_symbols: list[dict] = field(default_factory=list)
    signal_quality_summary: dict = field(default_factory=dict)
    calibration_summary: dict = field(default_factory=dict)
    controlled_paper_decision_summary: dict = field(default_factory=dict)
    paper_trade_readiness_summary: dict = field(default_factory=dict)
    fresh_validation_summary: dict = field(default_factory=dict)
    risk_hygiene_summary: dict = field(default_factory=dict)
    safety_summary: dict = field(default_factory=dict)
    threshold_changes_allowed: bool = False
    threshold_change_recommended: bool = False
    paper_trades_allowed: bool = False
    paper_trade_recommended: bool = False
    live_review_allowed: bool = False
    live_review_recommended: bool = False
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_strategy_review_checkpoint_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ExtendedObservationPlan:
    """Extended observation plan."""

    plan_status: str
    target_additional_runs: int
    target_additional_observations: int
    review_after_runs: int
    symbols: list[str]
    timeframe: str
    focus_symbols: list[str] = field(default_factory=list)
    focus_reasons: list[str] = field(default_factory=list)
    observe_only: bool = True
    paper_trades_allowed: bool = False
    live_review_allowed: bool = False
    threshold_changes_allowed: bool = False
    success_criteria: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    review_questions: list[str] = field(default_factory=list)
    recommended_commands: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_extended_observation_plan_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
