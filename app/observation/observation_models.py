"""Observation readiness models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ObservationReadinessResult:
    """Paper observation readiness result."""

    ready: bool
    checks: dict
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_observation_readiness_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


def _to_plain(value: Any) -> Any:
    """Convert nested values to JSON-friendly data."""
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    return value


@dataclass
class ObservationResult:
    """One symbol observation result."""

    symbol: str
    timeframe: str
    signal: Any = None
    risk_decision: Any = None
    paper_trade_result: Any = None
    action_taken: str = "observed"
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_observation_result_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _to_plain(asdict(self))


@dataclass
class ObservationRun:
    """One observation run summary."""

    run_id: str
    started_at: str
    completed_at: str | None
    status: str
    symbols_requested: int
    symbols_processed: int
    signals_generated: int
    risk_decisions_generated: int
    paper_trades_created: int
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    source: str = "crypto_hunter_observation_run_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _to_plain(asdict(self))


@dataclass
class ObservationReport:
    """Observation summary report."""

    generated_at: str
    runs_analyzed: int
    symbols_observed: list[str]
    signal_counts: dict
    top_signals: list[dict]
    risk_rejections: list[dict]
    paper_trades: list[dict]
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    early_recovery_candidates: list[dict] = field(default_factory=list)
    strongest_symbols: list[dict] = field(default_factory=list)
    dominant_blockers: list[dict] = field(default_factory=list)
    completed_runs_analyzed: int = 0
    refused_runs_count: int = 0
    total_attempted_runs: int = 0
    notes: list[str] = field(default_factory=list)
    source: str = "crypto_hunter_observation_report_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _to_plain(asdict(self))
