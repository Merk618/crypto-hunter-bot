"""Observation-only early recovery classification."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import Settings, get_settings
from app.observation.observation_metrics import flatten_results


@dataclass
class EarlyRecoveryCandidate:
    """Observation-only early recovery candidate."""

    symbol: str
    latest_score: float
    average_score: float
    repeated_count: int
    momentum_evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reason: str = ""
    action: str = "OBSERVE_ONLY"
    source: str = "crypto_hunter_early_recovery_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class EarlyRecoveryClassifier:
    """Classify observation-only early recovery candidates."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize classifier."""
        self.settings = settings or get_settings()

    def classify_runs(self, runs: list[dict]) -> list[EarlyRecoveryCandidate]:
        """Classify candidates from observation runs."""
        return self.classify_results(flatten_results([run for run in runs if run.get("status") == "completed"]))

    def classify_results(self, results: list[dict]) -> list[EarlyRecoveryCandidate]:
        """Classify candidates from observation results."""
        grouped: dict[str, list[dict]] = defaultdict(list)
        for result in results:
            grouped[self._symbol(result)].append(result)
        candidates = []
        for symbol, symbol_results in grouped.items():
            qualifying = [result for result in symbol_results if self._qualifies_single(result)]
            if len(qualifying) < self.settings.early_recovery_min_repeated_count:
                continue
            scores = [self._score(result) for result in qualifying]
            blockers = self._dedupe([blocker for result in qualifying for blocker in self._blockers(result)])
            warnings = self._dedupe([warning for result in qualifying for warning in self._warnings(result)])
            momentum = self._dedupe([item for result in qualifying for item in self._momentum_evidence(result)])
            candidates.append(
                EarlyRecoveryCandidate(
                    symbol=symbol,
                    latest_score=scores[0],
                    average_score=round(sum(scores) / len(scores), 2),
                    repeated_count=len(qualifying),
                    momentum_evidence=momentum,
                    blockers=blockers,
                    warnings=warnings,
                    reason="Repeated neutral-range observations with EMA 200 blocker and momentum evidence; observe only.",
                )
            )
        return sorted(candidates, key=lambda candidate: (candidate.average_score, candidate.latest_score), reverse=True)

    def _qualifies_single(self, result: dict) -> bool:
        """Return whether one result qualifies."""
        score = self._score(result)
        category = str(self._signal(result).get("category", "")).upper()
        if not (self.settings.early_recovery_min_score <= score <= self.settings.early_recovery_max_score):
            return False
        if category not in {"NEUTRAL", "BUY_WATCH", "WATCH"}:
            return False
        if self.settings.early_recovery_require_ema200_blocker and not self._has_ema_200_blocker(result):
            return False
        if self.settings.early_recovery_require_momentum_evidence and not self._momentum_evidence(result):
            return False
        risk = result.get("risk_decision") or {}
        if isinstance(risk, dict) and risk.get("approved"):
            return False
        return str(result.get("action_taken", "observed")).lower() in {"observed", "", "none"}

    def _signal(self, result: dict) -> dict:
        signal = result.get("signal") if isinstance(result, dict) else {}
        return signal if isinstance(signal, dict) else {}

    def _score(self, result: dict) -> float:
        try:
            return float(self._signal(result).get("score", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _symbol(self, result: dict) -> str:
        return str(result.get("symbol") or self._signal(result).get("symbol") or "UNKNOWN").upper().replace("-", "/")

    def _blockers(self, result: dict) -> list[Any]:
        return list(result.get("blockers") or []) + list(self._signal(result).get("blockers") or [])

    def _warnings(self, result: dict) -> list[Any]:
        return list(result.get("warnings") or []) + list(self._signal(result).get("warnings") or [])

    def _has_ema_200_blocker(self, result: dict) -> bool:
        text = " ".join(str(item).lower() for item in self._blockers(result))
        return "ema 200" in text or "ema_200" in text or "ema200" in text

    def _momentum_evidence(self, result: dict) -> list[str]:
        signal = self._signal(result)
        evidence = []
        text = " ".join(str(item).lower() for item in list(signal.get("reasons") or []) + list(result.get("reasons") or []))
        components = signal.get("component_scores") or {}
        if "macd" in text or float(components.get("momentum", 0) or 0) > 0:
            evidence.append("positive momentum component or MACD evidence")
        if "adx" in text:
            evidence.append("ADX trend strength evidence")
        if "obv" in text:
            evidence.append("OBV flow evidence")
        if "rsi" in text or "RSI 40-65" in str(signal.get("warnings") or ""):
            evidence.append("RSI recovery-zone evidence")
        return evidence

    def _dedupe(self, values: list[Any]) -> list[str]:
        seen = set()
        clean = []
        for value in values:
            text = str(value).strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                clean.append(text)
        return clean

