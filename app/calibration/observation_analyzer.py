"""Analyze paper observation runs for strategy calibration."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.calibration.calibration_models import StrategyCalibrationReport, SymbolCalibrationSummary
from app.calibration.threshold_recommendations import ThresholdRecommendationEngine
from app.config import Settings, get_settings


class ObservationAnalyzer:
    """Read-only analyzer for Phase 24 observation results."""

    def __init__(self, settings: Settings | None = None, recommender: ThresholdRecommendationEngine | None = None) -> None:
        """Initialize analyzer."""
        self.settings = settings or get_settings()
        self.recommender = recommender or ThresholdRecommendationEngine(self.settings)

    def analyze_runs(self, observation_runs: list[dict] | None) -> StrategyCalibrationReport:
        """Analyze observation runs and return a calibration report."""
        results = self._flatten_results(observation_runs or [])
        scores = [score for score in (self._score(result) for result in results) if score is not None]
        grouped: dict[str, list[dict]] = defaultdict(list)
        for result in results:
            grouped[self._symbol(result)].append(result)
        summaries = [self.analyze_symbol(symbol, symbol_results) for symbol, symbol_results in sorted(grouped.items())]
        findings = self.recommender.build_findings(summaries, len(results))
        recommendations = self.recommender.build_recommendations(summaries, len(results))
        conclusion = self._build_conclusion(len(observation_runs or []), len(results), summaries)
        return StrategyCalibrationReport(
            observations_analyzed=len(results),
            symbols_analyzed=len(summaries),
            overall_average_score=round(sum(scores) / len(scores), 2) if scores else None,
            category_distribution=self.calculate_category_distribution(results),
            blocker_distribution=self.calculate_blocker_distribution(results),
            warning_distribution=self.calculate_warning_distribution(results),
            symbol_summaries=summaries,
            findings=findings,
            threshold_recommendations=recommendations,
            conclusion=conclusion,
        )

    def analyze_symbol(self, symbol: str, observation_results: list[dict] | None) -> SymbolCalibrationSummary:
        """Summarize calibration behavior for one symbol."""
        results = observation_results or []
        scores = [score for score in (self._score(result) for result in results) if score is not None]
        categories = self.calculate_category_distribution(results)
        risks = Counter(str(self._signal(result).get("risk_level", "UNKNOWN")) for result in results)
        blockers = self.calculate_blocker_distribution(results)
        warnings = self.calculate_warning_distribution(results)
        ema_rate = self._rate(results, self._has_ema_200_blocker)
        low_rate = self._rate(results, lambda result: (self._score(result) or 0) < 65)
        notes = self._symbol_notes(symbol, results, ema_rate, low_rate)
        return SymbolCalibrationSummary(
            symbol=symbol,
            observations_count=len(results),
            average_score=round(sum(scores) / len(scores), 2) if scores else None,
            max_score=max(scores) if scores else None,
            min_score=min(scores) if scores else None,
            latest_score=scores[0] if scores else None,
            categories_count=categories,
            risk_levels_count=dict(risks),
            most_common_blockers=[{"text": text, "count": count} for text, count in Counter(blockers).most_common(5)],
            most_common_warnings=[{"text": text, "count": count} for text, count in Counter(warnings).most_common(5)],
            ema_200_blocker_rate=round(ema_rate, 4),
            low_score_rate=round(low_rate, 4),
            strong_buy_count=categories.get("STRONG_BUY", 0),
            buy_watch_count=categories.get("BUY_WATCH", 0),
            neutral_count=categories.get("NEUTRAL", 0),
            weak_count=categories.get("WEAK", 0),
            avoid_sell_count=categories.get("AVOID_SELL", 0),
            notes=notes,
        )

    def calculate_category_distribution(self, results: list[dict]) -> dict[str, int]:
        """Count signal categories."""
        return dict(Counter(str(self._signal(result).get("category", "UNKNOWN")) for result in results))

    def calculate_blocker_distribution(self, results: list[dict]) -> Counter:
        """Count deduped blocker text."""
        return dict(Counter(blocker for result in results for blocker in self._deduped_texts(self._blockers(result))))

    def calculate_warning_distribution(self, results: list[dict]) -> Counter:
        """Count deduped warning text."""
        return dict(Counter(warning for result in results for warning in self._deduped_texts(self._warnings(result))))

    def detect_common_blockers(self, results: list[dict]) -> list[dict]:
        """Return common blockers as dictionaries."""
        return [{"text": text, "count": count} for text, count in Counter(self.calculate_blocker_distribution(results)).most_common()]

    def detect_score_bottlenecks(self, results: list[dict]) -> dict:
        """Return score bottleneck summary."""
        scores = [score for score in (self._score(result) for result in results) if score is not None]
        low_count = sum(1 for score in scores if score < 65)
        neutral_or_weak = sum(1 for result in results if str(self._signal(result).get("category", "")).upper() in {"NEUTRAL", "WEAK", "AVOID_SELL"})
        return {
            "sample_size": len(scores),
            "low_score_count": low_count,
            "low_score_rate": round(low_count / len(scores), 4) if scores else 0.0,
            "neutral_weak_avoid_count": neutral_or_weak,
            "consistently_low": bool(scores) and low_count / len(scores) >= self.settings.calibration_warn_low_score_rate,
        }

    def _flatten_results(self, runs: list[dict]) -> list[dict]:
        """Flatten Phase 24 run dictionaries to result dictionaries."""
        results: list[dict] = []
        for run in runs:
            if not isinstance(run, dict):
                continue
            for result in run.get("results", []) or []:
                if isinstance(result, dict):
                    results.append(result)
        return results

    def _symbol(self, result: dict) -> str:
        """Return normalized result symbol."""
        return str(result.get("symbol") or self._signal(result).get("symbol") or "UNKNOWN").upper().replace("-", "/")

    def _signal(self, result: dict) -> dict:
        """Return signal dictionary safely."""
        signal = result.get("signal") if isinstance(result, dict) else {}
        return signal if isinstance(signal, dict) else {}

    def _score(self, result: dict) -> float | None:
        """Return signal score if available."""
        value = self._signal(result).get("score")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _blockers(self, result: dict) -> list[Any]:
        """Collect result and signal blockers."""
        return list(result.get("blockers") or []) + list(self._signal(result).get("blockers") or [])

    def _warnings(self, result: dict) -> list[Any]:
        """Collect result and signal warnings."""
        return list(result.get("warnings") or []) + list(self._signal(result).get("warnings") or [])

    def _deduped_texts(self, values: list[Any]) -> list[str]:
        """Return normalized, deduped text values preserving order."""
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

    def _has_ema_200_blocker(self, result: dict) -> bool:
        """Return whether a result was blocked by EMA 200 trend logic."""
        text = " ".join(self._deduped_texts(self._blockers(result))).lower()
        return "ema 200" in text or "ema_200" in text or "ema200" in text

    def _rate(self, results: list[dict], predicate) -> float:
        """Return predicate hit rate."""
        if not results:
            return 0.0
        return sum(1 for result in results if predicate(result)) / len(results)

    def _symbol_notes(self, symbol: str, results: list[dict], ema_rate: float, low_rate: float) -> list[str]:
        """Build human-readable symbol notes."""
        notes: list[str] = []
        if not results:
            return ["No observation results available."]
        if ema_rate >= self.settings.calibration_warn_ema200_blocker_rate:
            notes.append(f"{symbol} is frequently blocked by the EMA 200 trend filter.")
        if low_rate >= self.settings.calibration_warn_low_score_rate:
            notes.append(f"{symbol} scores are consistently below BUY_WATCH/STRONG_BUY levels.")
        if any(self._has_positive_momentum(result) and self._has_ema_200_blocker(result) for result in results):
            notes.append("Momentum evidence exists, but trend filter is still blocking trade consideration.")
        if not notes:
            notes.append("No dominant calibration bottleneck detected.")
        return notes

    def _has_positive_momentum(self, result: dict) -> bool:
        """Infer positive momentum from reasons/component scores."""
        signal = self._signal(result)
        text = " ".join(str(item).lower() for item in (signal.get("reasons") or []) + (result.get("reasons") or []))
        components = signal.get("component_scores") or {}
        momentum_score = components.get("momentum") if isinstance(components, dict) else None
        try:
            has_score = float(momentum_score) > 0
        except (TypeError, ValueError):
            has_score = False
        return has_score or "macd" in text or "momentum" in text or "adx" in text

    def _build_conclusion(self, run_count: int, result_count: int, summaries: list[SymbolCalibrationSummary]) -> str:
        """Build report conclusion."""
        if result_count == 0:
            return "No paper observation data is available yet. Run observation mode before changing any strategy assumptions."
        if run_count <= 1:
            return "Only one observation run is available, so more observation data is needed before changing thresholds."
        if result_count < self.settings.calibration_min_sample_size_for_changes:
            return "The sample is still small. Continue the paper observation window before changing thresholds."
        if any(summary.ema_200_blocker_rate >= self.settings.calibration_warn_ema200_blocker_rate for summary in summaries):
            return "EMA 200 trend filtering is a dominant bottleneck. Keep trade filters conservative and consider an observation-only early recovery tag."
        return "Calibration sample is usable for review, but recommendations remain read-only and require manual approval."
