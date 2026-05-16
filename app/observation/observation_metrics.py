"""Observation window metrics helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any


def _signal(result: dict) -> dict:
    """Return a result signal dictionary safely."""
    signal = result.get("signal") if isinstance(result, dict) else {}
    return signal if isinstance(signal, dict) else {}


def _score(result: dict) -> float | None:
    """Return a numeric score when available."""
    try:
        return float(_signal(result).get("score"))
    except (TypeError, ValueError):
        return None


def _texts(values: list[Any]) -> list[str]:
    """Normalize and dedupe text values."""
    seen: set[str] = set()
    clean: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in {"[", "]"}:
            continue
        key = text.lower()
        if key not in seen:
            seen.add(key)
            clean.append(text)
    return clean


def _symbol(result: dict) -> str:
    """Return normalized symbol."""
    return str(result.get("symbol") or _signal(result).get("symbol") or "UNKNOWN").upper().replace("-", "/")


def flatten_results(runs: list[dict]) -> list[dict]:
    """Flatten observation runs into result dictionaries."""
    return [result for run in runs for result in (run.get("results", []) or []) if isinstance(result, dict)]


@dataclass
class ObservationMetrics:
    """Per-symbol metrics across an observation window."""

    symbol: str
    observations: int
    average_score: float | None
    max_score: float | None
    min_score: float | None
    latest_score: float | None
    category_counts: dict[str, int] = field(default_factory=dict)
    blocker_counts: dict[str, int] = field(default_factory=dict)
    warning_counts: dict[str, int] = field(default_factory=dict)
    improving_score_trend: bool = False
    repeated_neutral_or_better_count: int = 0
    repeated_ema200_blocker_count: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


def summarize_scores_by_symbol(results: list[dict]) -> dict[str, dict]:
    """Return average, max, min, and latest score by symbol."""
    grouped: dict[str, list[float]] = defaultdict(list)
    for result in results:
        score = _score(result)
        if score is not None:
            grouped[_symbol(result)].append(score)
    return {
        symbol: {
            "average_score": round(sum(scores) / len(scores), 2),
            "max_score": max(scores),
            "min_score": min(scores),
            "latest_score": scores[0],
        }
        for symbol, scores in grouped.items()
    }


def summarize_categories(results: list[dict]) -> dict[str, int]:
    """Count signal categories."""
    return dict(Counter(str(_signal(result).get("category", "UNKNOWN")) for result in results))


def summarize_blockers(results: list[dict]) -> dict[str, int]:
    """Count deduped blocker text."""
    counter: Counter = Counter()
    for result in results:
        blockers = list(result.get("blockers") or []) + list(_signal(result).get("blockers") or [])
        counter.update(_texts(blockers))
    return dict(counter)


def summarize_warnings(results: list[dict]) -> dict[str, int]:
    """Count deduped warning text."""
    counter: Counter = Counter()
    for result in results:
        warnings = list(result.get("warnings") or []) + list(_signal(result).get("warnings") or [])
        counter.update(_texts(warnings))
    return dict(counter)


def detect_repeated_watchlist_candidates(results: list[dict], min_count: int = 2) -> list[dict]:
    """Detect symbols repeatedly reaching NEUTRAL or better."""
    counts: Counter = Counter()
    best_scores: dict[str, float] = {}
    for result in results:
        category = str(_signal(result).get("category", "")).upper()
        if category in {"NEUTRAL", "BUY_WATCH", "STRONG_BUY"}:
            symbol = _symbol(result)
            counts[symbol] += 1
            score = _score(result) or 0
            best_scores[symbol] = max(best_scores.get(symbol, 0), score)
    return [
        {"symbol": symbol, "count": count, "best_score": best_scores.get(symbol, 0)}
        for symbol, count in counts.most_common()
        if count >= min_count
    ]


def detect_improving_scores(results: list[dict]) -> dict[str, bool]:
    """Detect whether each symbol has an improving score trend."""
    grouped: dict[str, list[float]] = defaultdict(list)
    for result in results:
        score = _score(result)
        if score is not None:
            grouped[_symbol(result)].append(score)
    return {symbol: len(scores) >= 2 and scores[0] > scores[-1] for symbol, scores in grouped.items()}


def calculate_calibration_readiness(runs_analyzed: int, min_runs_required: int) -> str:
    """Return calibration readiness from run count."""
    if runs_analyzed < min_runs_required:
        return "NOT_READY"
    if runs_analyzed < max(min_runs_required * 2, min_runs_required + 1):
        return "PARTIAL"
    return "READY_FOR_REVIEW"


def build_symbol_metrics(results: list[dict]) -> list[ObservationMetrics]:
    """Build per-symbol metrics."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    improving = detect_improving_scores(results)
    for result in results:
        grouped[_symbol(result)].append(result)
    metrics: list[ObservationMetrics] = []
    for symbol, symbol_results in sorted(grouped.items()):
        scores = [score for score in (_score(result) for result in symbol_results) if score is not None]
        categories = summarize_categories(symbol_results)
        blockers = summarize_blockers(symbol_results)
        warnings = summarize_warnings(symbol_results)
        ema_count = sum(count for text, count in blockers.items() if "ema 200" in text.lower() or "ema_200" in text.lower() or "ema200" in text.lower())
        neutral_or_better = sum(categories.get(category, 0) for category in ("NEUTRAL", "BUY_WATCH", "STRONG_BUY"))
        notes = []
        if improving.get(symbol):
            notes.append("Scores are improving across the window.")
        if ema_count:
            notes.append("EMA 200 remains a repeated blocker.")
        metrics.append(
            ObservationMetrics(
                symbol=symbol,
                observations=len(symbol_results),
                average_score=round(sum(scores) / len(scores), 2) if scores else None,
                max_score=max(scores) if scores else None,
                min_score=min(scores) if scores else None,
                latest_score=scores[0] if scores else None,
                category_counts=categories,
                blocker_counts=blockers,
                warning_counts=warnings,
                improving_score_trend=improving.get(symbol, False),
                repeated_neutral_or_better_count=neutral_or_better,
                repeated_ema200_blocker_count=ema_count,
                notes=notes or ["No repeated window pattern detected."],
            )
        )
    return metrics

