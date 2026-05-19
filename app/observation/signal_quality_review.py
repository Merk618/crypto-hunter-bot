"""Read-only signal quality review for persisted observations."""

from __future__ import annotations

from collections import Counter, defaultdict

from app.config import Settings, get_settings
from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_metrics import flatten_results, summarize_blockers, summarize_warnings
from app.observation.signal_quality_models import SignalQualityReviewReport, SignalQualitySymbolSummary


class SignalQualityReviewService:
    """Analyze why observations are not reaching STRONG_BUY or risk-approved states."""

    def __init__(self, settings: Settings | None = None, hydration: ObservationHydrationService | None = None, early_recovery: EarlyRecoveryWatchlistService | None = None) -> None:
        """Initialize signal quality service."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.early_recovery = early_recovery or EarlyRecoveryWatchlistService(settings=self.settings, hydration=self.hydration)

    def review(self, runs: list[dict] | None = None) -> dict:
        """Return full signal quality review."""
        if not self.settings.signal_quality_review_enabled:
            return self._empty("Signal quality review disabled.", disabled=True)
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.signal_quality_review_history_limit)
        completed = [run for run in runs if run.get("status") == "completed"]
        results = flatten_results(completed)
        if not results:
            return self._empty("No persisted observation results available.")
        early = self.early_recovery.get_report() if runs is None else EarlyRecoveryWatchlistService(settings=self.settings, runs=completed).get_report()
        early_symbols = {item.get("symbol") for item in early.get("candidates", [])}
        symbol_summaries = [summary.to_dict() for summary in self._symbol_summaries(results, early_symbols)]
        scores = [score for score in (self._score(result) for result in results) if score is not None]
        categories = Counter(self._category(result) for result in results)
        blockers = summarize_blockers(results)
        warnings = summarize_warnings(results)
        dominant = self._dominant_items(blockers, len(results))
        strong_buy_count = categories.get("STRONG_BUY", 0)
        risk_approved_count = sum(1 for result in results if (result.get("risk_decision") or {}).get("approved"))
        report = SignalQualityReviewReport(
            observations_analyzed=len(results),
            completed_runs_analyzed=len(completed),
            symbols_analyzed=len(symbol_summaries),
            average_score=round(sum(scores) / len(scores), 2) if scores else None,
            max_score=max(scores) if scores else None,
            strong_buy_count=strong_buy_count,
            buy_watch_count=categories.get("BUY_WATCH", 0),
            neutral_count=categories.get("NEUTRAL", 0),
            weak_count=categories.get("WEAK", 0),
            risk_approved_count=risk_approved_count,
            early_recovery_count=len(early_symbols),
            near_buy_watch_count=sum(1 for score in scores if score >= self.settings.signal_quality_review_near_buy_watch_score),
            near_strong_buy_count=sum(1 for score in scores if score >= self.settings.signal_quality_review_near_strong_buy_score),
            dominant_blockers=dominant,
            blocker_distribution=blockers,
            warning_distribution=warnings,
            symbol_summaries=symbol_summaries,
            findings=self._findings(results, dominant, strong_buy_count, risk_approved_count, len(early_symbols)),
            warnings=self._warnings(completed, results, early),
            blockers=[] if len(results) >= self.settings.signal_quality_review_min_observations else ["Signal quality review needs more observations."],
            recommended_next_actions=self._actions(strong_buy_count, risk_approved_count, dominant, len(early_symbols)),
            threshold_change_recommended=False,
            paper_trade_observation_recommended=False,
            live_review_recommended=False,
        )
        return report.to_dict()

    def symbols(self, runs: list[dict] | None = None) -> dict:
        """Return symbol summaries."""
        report = self.review(runs=runs)
        return {"symbols": report.get("symbol_summaries", []), "source": "crypto_hunter_signal_quality_symbols_v1"}

    def symbol(self, symbol: str, runs: list[dict] | None = None) -> dict:
        """Return one symbol summary."""
        normalized = symbol.strip().upper().replace("-", "/")
        for item in self.symbols(runs=runs).get("symbols", []):
            if item.get("symbol") == normalized:
                return item
        return {"symbol": normalized, "found": False, "source": "crypto_hunter_signal_quality_symbol_lookup_v1"}

    def _symbol_summaries(self, results: list[dict], early_symbols: set[str]) -> list[SignalQualitySymbolSummary]:
        """Build per-symbol quality summaries."""
        grouped: dict[str, list[dict]] = defaultdict(list)
        for result in results:
            grouped[self._symbol(result)].append(result)
        summaries: list[SignalQualitySymbolSummary] = []
        rank = {"STRONG_BUY": 5, "BUY_WATCH": 4, "NEUTRAL": 3, "WEAK": 2, "AVOID_SELL": 1, "UNKNOWN": 0}
        for symbol, items in sorted(grouped.items()):
            scores = [score for score in (self._score(item) for item in items) if score is not None]
            categories = Counter(self._category(item) for item in items)
            blockers = summarize_blockers(items)
            warnings = summarize_warnings(items)
            strongest = max(categories, key=lambda category: rank.get(category, 0)) if categories else "UNKNOWN"
            summaries.append(
                SignalQualitySymbolSummary(
                    symbol=symbol,
                    observations=len(items),
                    average_score=round(sum(scores) / len(scores), 2) if scores else None,
                    latest_score=scores[0] if scores else None,
                    max_score=max(scores) if scores else None,
                    min_score=min(scores) if scores else None,
                    latest_category=self._category(items[0]) if items else "UNKNOWN",
                    strongest_category=strongest,
                    strong_buy_count=categories.get("STRONG_BUY", 0),
                    buy_watch_count=categories.get("BUY_WATCH", 0),
                    neutral_count=categories.get("NEUTRAL", 0),
                    weak_count=categories.get("WEAK", 0),
                    risk_approved_count=sum(1 for item in items if (item.get("risk_decision") or {}).get("approved")),
                    dominant_blockers=self._top_items(blockers),
                    dominant_warnings=self._top_items(warnings),
                    early_recovery_candidate=symbol in early_symbols,
                    score_trend=self._trend(scores),
                    near_buy_watch_count=sum(1 for score in scores if score >= self.settings.signal_quality_review_near_buy_watch_score),
                    near_strong_buy_count=sum(1 for score in scores if score >= self.settings.signal_quality_review_near_strong_buy_score),
                    recommendation=self._symbol_recommendation(scores, categories, symbol in early_symbols),
                )
            )
        return summaries

    def _findings(self, results: list[dict], dominant: list[dict], strong_buy_count: int, risk_approved_count: int, early_count: int) -> list[dict]:
        """Build review findings."""
        findings: list[dict] = []
        if any("ema 200" in item["text"].lower() or "ema200" in item["text"].lower() or "ema_200" in item["text"].lower() for item in dominant):
            findings.append({"finding_type": "DOMINANT_EMA_200_BLOCKER", "message": "EMA 200 remains a dominant blocker and should continue to block trade execution."})
        if strong_buy_count == 0:
            findings.append({"finding_type": "NO_STRONG_BUY_OBSERVATIONS", "message": "No observations reached STRONG_BUY."})
        if risk_approved_count == 0:
            findings.append({"finding_type": "NO_RISK_APPROVED_OBSERVATIONS", "message": "No observations were risk-approved."})
        if early_count:
            findings.append({"finding_type": "EARLY_RECOVERY_PRESENT", "message": "Early recovery candidates exist but remain observe-only."})
        if len(results) < self.settings.signal_quality_review_min_observations:
            findings.append({"finding_type": "INSUFFICIENT_OBSERVATIONS", "message": "A larger persisted observation window is recommended."})
        return findings

    def _warnings(self, completed: list[dict], results: list[dict], early: dict) -> list[str]:
        """Build warning strings."""
        warnings = ["Phase 39 does not change thresholds or enable paper/live trading."]
        if len(completed) < self.settings.signal_quality_review_min_completed_runs:
            warnings.append("More completed observation runs are recommended.")
        if len(results) < self.settings.signal_quality_review_min_observations:
            warnings.append("More persisted observation results are recommended.")
        if early.get("candidates"):
            warnings.append("Early recovery candidates are observe-only and not trade signals.")
        return list(dict.fromkeys(warnings))

    def _actions(self, strong_buy_count: int, risk_approved_count: int, dominant: list[dict], early_count: int) -> list[str]:
        """Return next actions."""
        actions = ["Continue observation-only mode.", "Keep thresholds unchanged."]
        if strong_buy_count == 0:
            actions.append("Collect more persisted observations until repeated STRONG_BUY signals appear.")
        if risk_approved_count == 0:
            actions.append("Wait for clean risk-approved observations before any paper review.")
        if dominant:
            actions.append("Review dominant blockers manually; keep EMA 200 required for trade execution.")
        if early_count:
            actions.append("Track early recovery candidates as OBSERVE_ONLY.")
        actions.append("Do not enable paper trades or live trading.")
        return list(dict.fromkeys(actions))

    def _empty(self, message: str, disabled: bool = False) -> dict:
        """Return empty report."""
        report = SignalQualityReviewReport(
            observations_analyzed=0,
            completed_runs_analyzed=0,
            symbols_analyzed=0,
            average_score=None,
            max_score=None,
            strong_buy_count=0,
            buy_watch_count=0,
            neutral_count=0,
            weak_count=0,
            risk_approved_count=0,
            early_recovery_count=0,
            near_buy_watch_count=0,
            near_strong_buy_count=0,
            blockers=[] if disabled else [message],
            warnings=[message] if disabled else [],
            recommended_next_actions=["Run more persisted observation windows."],
        )
        return report.to_dict()

    def _score(self, result: dict) -> float | None:
        """Return signal score."""
        try:
            return float((result.get("signal") or {}).get("score"))
        except (TypeError, ValueError):
            return None

    def _category(self, result: dict) -> str:
        """Return normalized category."""
        return str((result.get("signal") or {}).get("category") or "UNKNOWN").upper()

    def _symbol(self, result: dict) -> str:
        """Return normalized symbol."""
        return str(result.get("symbol") or (result.get("signal") or {}).get("symbol") or "UNKNOWN").upper().replace("-", "/")

    def _top_items(self, values: dict[str, int]) -> list[dict]:
        """Return top count items."""
        return [{"text": text, "count": count} for text, count in Counter(values).most_common(5)]

    def _dominant_items(self, values: dict[str, int], total: int) -> list[dict]:
        """Return dominant blockers over threshold."""
        if not total:
            return []
        return [
            {"text": text, "count": count, "rate": round(count / total, 4)}
            for text, count in Counter(values).most_common()
            if count / total >= self.settings.signal_quality_review_dominant_blocker_threshold
        ]

    def _trend(self, scores: list[float]) -> str:
        """Classify score trend."""
        if len(scores) < 2:
            return "INSUFFICIENT_DATA"
        delta = scores[0] - scores[-1]
        if delta > 1:
            return "IMPROVING"
        if delta < -1:
            return "DETERIORATING"
        return "FLAT"

    def _symbol_recommendation(self, scores: list[float], categories: Counter, early: bool) -> str:
        """Return symbol-level recommendation."""
        if categories.get("STRONG_BUY", 0):
            return "REVIEW_RISK_APPROVAL_HISTORY"
        if any(score >= self.settings.signal_quality_review_near_buy_watch_score for score in scores):
            return "WATCH_CLOSELY_OBSERVE_ONLY"
        if early:
            return "EARLY_RECOVERY_OBSERVE_ONLY"
        return "CONTINUE_OBSERVATION_ONLY"
