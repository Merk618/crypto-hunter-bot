"""Observation report aggregation."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.observation.observation_models import ObservationReport


def build_observation_report(runs: list[dict], limit: int = 100) -> ObservationReport:
    """Summarize recent observation runs."""
    selected = runs[:limit]
    completed = [run for run in selected if run.get("status", "completed") == "completed"]
    refused = [run for run in selected if run.get("status") == "refused"]
    results = [result for run in completed for result in run.get("results", [])]
    signal_counts = Counter(str((result.get("signal") or {}).get("category", "NONE")) for result in results)
    top_signals = sorted(
        [result for result in results if result.get("signal")],
        key=lambda item: float((item.get("signal") or {}).get("score", 0) or 0),
        reverse=True,
    )[:10]
    risk_rejections = [result for result in results if result.get("risk_decision") and not (result.get("risk_decision") or {}).get("approved")]
    paper_trades = [result for result in results if result.get("paper_trade_result")]
    warnings = []
    blockers = []
    for run in completed:
        warnings.extend(run.get("warnings", []))
        blockers.extend(run.get("blockers", []))
    dominant_blockers = [{"text": text, "count": count} for text, count in Counter(blockers + [item for result in results for item in (result.get("blockers") or [])]).most_common(5)]
    strongest_symbols = _strongest_symbols(results)
    early_report = EarlyRecoveryWatchlistService(runs=completed).get_report()
    return ObservationReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        runs_analyzed=len(completed),
        symbols_observed=sorted({result.get("symbol") for result in results if result.get("symbol")}),
        signal_counts=dict(signal_counts),
        top_signals=top_signals,
        risk_rejections=risk_rejections[:20],
        paper_trades=paper_trades[:20],
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
        early_recovery_candidates=early_report.get("candidates", []),
        strongest_symbols=strongest_symbols,
        dominant_blockers=dominant_blockers,
        completed_runs_analyzed=len(completed),
        refused_runs_count=len(refused),
        total_attempted_runs=len(selected),
        notes=[
            "Early recovery candidates are OBSERVE ONLY and not trade signals.",
            "EMA 200 remains required for trade execution.",
        ],
    )


def _strongest_symbols(results: list[dict]) -> list[dict]:
    """Return strongest symbols by observed max score."""
    rows: dict[str, dict] = {}
    for result in results:
        signal = result.get("signal") or {}
        symbol = str(result.get("symbol") or signal.get("symbol") or "UNKNOWN")
        score = float(signal.get("score", 0) or 0)
        row = rows.setdefault(symbol, {"symbol": symbol, "max_score": score, "latest_score": score, "category": signal.get("category")})
        row["max_score"] = max(row["max_score"], score)
        row["latest_score"] = score
        row["category"] = signal.get("category")
    return sorted(rows.values(), key=lambda item: (item["max_score"], item["latest_score"]), reverse=True)
