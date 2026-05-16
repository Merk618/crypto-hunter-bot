"""Observation window summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.config import Settings, get_settings
from app.observation.observation_metrics import (
    build_symbol_metrics,
    calculate_calibration_readiness,
    detect_repeated_watchlist_candidates,
    flatten_results,
    summarize_blockers,
    summarize_categories,
    summarize_scores_by_symbol,
    summarize_warnings,
)


@dataclass
class ObservationWindowSummary:
    """Summary across a longer observation window."""

    session_id: str
    runs_analyzed: int
    symbols_observed: list[str]
    total_signals: int
    category_distribution: dict
    average_score_by_symbol: dict
    max_score_by_symbol: dict
    blocker_distribution: dict
    warning_distribution: dict
    strongest_observed_signal: dict | None
    repeated_watchlist_candidates: list[dict]
    paper_trades_created: int
    calibration_readiness: str
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metrics_by_symbol: list[dict] = field(default_factory=list)
    source: str = "crypto_hunter_observation_window_summary_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


def build_observation_window_summary(session_id: str, runs: list[dict], settings: Settings | None = None) -> ObservationWindowSummary:
    """Build a summary from observation window runs."""
    settings = settings or get_settings()
    results = flatten_results(runs)
    scores = summarize_scores_by_symbol(results)
    strongest = sorted(
        [result for result in results if result.get("signal")],
        key=lambda result: float((result.get("signal") or {}).get("score", 0) or 0),
        reverse=True,
    )
    warnings = []
    blockers = []
    for run in runs:
        warnings.extend(run.get("warnings") or [])
        blockers.extend(run.get("blockers") or [])
    return ObservationWindowSummary(
        session_id=session_id,
        runs_analyzed=len(runs),
        symbols_observed=sorted({str(result.get("symbol")) for result in results if result.get("symbol")}),
        total_signals=sum(1 for result in results if result.get("signal")),
        category_distribution=summarize_categories(results),
        average_score_by_symbol={symbol: data["average_score"] for symbol, data in scores.items()},
        max_score_by_symbol={symbol: data["max_score"] for symbol, data in scores.items()},
        blocker_distribution=summarize_blockers(results),
        warning_distribution=summarize_warnings(results),
        strongest_observed_signal=strongest[0] if strongest else None,
        repeated_watchlist_candidates=detect_repeated_watchlist_candidates(results),
        paper_trades_created=sum(int(run.get("paper_trades_created", 0) or 0) for run in runs),
        calibration_readiness=calculate_calibration_readiness(len(runs), settings.observation_window_min_runs_for_summary),
        warnings=list(dict.fromkeys(str(item) for item in warnings if item)),
        blockers=list(dict.fromkeys(str(item) for item in blockers if item)),
        metrics_by_symbol=[metric.to_dict() for metric in build_symbol_metrics(results)],
    )

