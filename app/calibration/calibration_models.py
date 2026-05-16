"""Calibration report models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _to_plain(value: Any) -> Any:
    """Convert nested dataclass-like values to JSON-friendly data."""
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
class SymbolCalibrationSummary:
    """Calibration summary for one observed symbol."""

    symbol: str
    observations_count: int
    average_score: float | None
    max_score: float | None
    min_score: float | None
    latest_score: float | None
    categories_count: dict[str, int] = field(default_factory=dict)
    risk_levels_count: dict[str, int] = field(default_factory=dict)
    most_common_blockers: list[dict] = field(default_factory=list)
    most_common_warnings: list[dict] = field(default_factory=list)
    ema_200_blocker_rate: float = 0.0
    low_score_rate: float = 0.0
    strong_buy_count: int = 0
    buy_watch_count: int = 0
    neutral_count: int = 0
    weak_count: int = 0
    avoid_sell_count: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _to_plain(asdict(self))


@dataclass
class CalibrationFinding:
    """One strategy calibration finding."""

    severity: str
    finding_type: str
    message: str
    affected_symbols: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    recommendation: str = ""
    auto_apply_allowed: bool = False

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _to_plain(asdict(self))


@dataclass
class ThresholdRecommendation:
    """Read-only threshold recommendation."""

    parameter_name: str
    current_value: Any
    suggested_value: Any
    reason: str
    confidence: str
    sample_size: int
    auto_apply_allowed: bool = False

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _to_plain(asdict(self))


@dataclass
class StrategyCalibrationReport:
    """Read-only strategy calibration report."""

    observations_analyzed: int
    symbols_analyzed: int
    overall_average_score: float | None
    category_distribution: dict[str, int] = field(default_factory=dict)
    blocker_distribution: dict[str, int] = field(default_factory=dict)
    warning_distribution: dict[str, int] = field(default_factory=dict)
    symbol_summaries: list[SymbolCalibrationSummary] = field(default_factory=list)
    findings: list[CalibrationFinding] = field(default_factory=list)
    threshold_recommendations: list[ThresholdRecommendation] = field(default_factory=list)
    conclusion: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_strategy_calibration_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _to_plain(asdict(self))

