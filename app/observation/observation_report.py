"""Observation report aggregation."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.observation.observation_models import ObservationReport


def build_observation_report(runs: list[dict], limit: int = 100) -> ObservationReport:
    """Summarize recent observation runs."""
    selected = runs[:limit]
    results = [result for run in selected for result in run.get("results", [])]
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
    for run in selected:
        warnings.extend(run.get("warnings", []))
        blockers.extend(run.get("blockers", []))
    return ObservationReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        runs_analyzed=len(selected),
        symbols_observed=sorted({result.get("symbol") for result in results if result.get("symbol")}),
        signal_counts=dict(signal_counts),
        top_signals=top_signals,
        risk_rejections=risk_rejections[:20],
        paper_trades=paper_trades[:20],
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )
