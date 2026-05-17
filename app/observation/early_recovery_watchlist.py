"""Observation-only early recovery watchlist."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.observation.early_recovery import EarlyRecoveryCandidate, EarlyRecoveryClassifier
from app.observation.observation_hydration import ObservationHydrationService


@dataclass
class EarlyRecoveryWatchlistItem:
    """Ranked early recovery watchlist item."""

    symbol: str
    rank: int
    latest_score: float
    average_score: float
    max_score: float
    repeated_count: int
    latest_category: str
    momentum_evidence: list[str] = field(default_factory=list)
    dominant_blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reason: str = ""
    action: str = "OBSERVE_ONLY"
    trade_allowed: bool = False
    paper_trade_allowed: bool = False
    live_trade_allowed: bool = False
    source: str = "crypto_hunter_early_recovery_watchlist_item_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class EarlyRecoveryWatchlistReport:
    """Early recovery watchlist report."""

    enabled: bool
    observe_only: bool
    candidates: list[dict] = field(default_factory=list)
    excluded_symbols: list[str] = field(default_factory=list)
    dominant_blockers: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_early_recovery_watchlist_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class EarlyRecoveryWatchlistService:
    """Build observation-only early recovery watchlists from persisted history."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        classifier: EarlyRecoveryClassifier | None = None,
        runs: list[dict] | None = None,
    ) -> None:
        """Initialize watchlist service."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.classifier = classifier or EarlyRecoveryClassifier(self.settings)
        self._runs = runs

    def get_watchlist(self) -> dict:
        """Return ranked watchlist."""
        return {"candidates": [item.to_dict() for item in self._items()], "source": "crypto_hunter_early_recovery_watchlist_items_v1"}

    def get_symbol(self, symbol: str) -> dict:
        """Return one watchlist item by symbol."""
        normalized = symbol.strip().upper().replace("-", "/")
        for item in self._items():
            if item.symbol == normalized:
                return item.to_dict()
        return {"symbol": normalized, "candidate": None, "action": "OBSERVE_ONLY", "source": "crypto_hunter_early_recovery_watchlist_item_lookup_v1"}

    def get_report(self) -> dict:
        """Return full early recovery watchlist report."""
        runs = self._load_runs()
        items = self._items(runs)
        results = [result for run in runs if run.get("status") == "completed" for result in run.get("results", [])]
        all_symbols = sorted({str(result.get("symbol", "")).upper().replace("-", "/") for result in results if result.get("symbol")})
        included = {item.symbol for item in items}
        blockers = self._dominant_blockers(results)
        report = EarlyRecoveryWatchlistReport(
            enabled=self.settings.early_recovery_watchlist_enabled,
            observe_only=self.settings.early_recovery_observe_only,
            candidates=[item.to_dict() for item in items],
            excluded_symbols=[symbol for symbol in all_symbols if symbol not in included],
            dominant_blockers=blockers,
            warnings=["Early recovery candidates are OBSERVE ONLY and not trade signals."],
            blockers=[] if self.settings.early_recovery_watchlist_enabled else ["Early recovery watchlist disabled"],
            recommended_next_actions=[
                "Review candidates across more observation windows.",
                "Keep EMA 200 required for trade execution.",
                "Do not enable paper or live trades from early recovery tags.",
            ],
        )
        return report.to_dict()

    def rank_candidates(self, candidates: list[EarlyRecoveryCandidate]) -> list[EarlyRecoveryWatchlistItem]:
        """Rank classifier candidates."""
        sorted_candidates = sorted(candidates, key=lambda item: (item.average_score, item.repeated_count, item.latest_score), reverse=True)
        return [self._item_from_candidate(candidate, rank) for rank, candidate in enumerate(sorted_candidates[: self.settings.early_recovery_max_candidates], start=1)]

    def explain_candidate(self, symbol: str) -> dict:
        """Explain one candidate."""
        item = self.get_symbol(symbol)
        if not item.get("candidate", True):
            return item
        item["explanation"] = "This symbol repeatedly reached the neutral recovery score band while still blocked by EMA 200. It remains observe-only."
        return item

    def _items(self, runs: list[dict] | None = None) -> list[EarlyRecoveryWatchlistItem]:
        """Return ranked items from runs."""
        runs = runs if runs is not None else self._load_runs()
        return self.rank_candidates(self.classifier.classify_runs(runs))

    def _load_runs(self) -> list[dict]:
        """Load runs from injected memory or persisted history."""
        if self._runs is not None:
            return self._runs
        return self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)

    def _item_from_candidate(self, candidate: EarlyRecoveryCandidate, rank: int) -> EarlyRecoveryWatchlistItem:
        """Convert classifier candidate to watchlist item."""
        return EarlyRecoveryWatchlistItem(
            symbol=candidate.symbol,
            rank=rank,
            latest_score=candidate.latest_score,
            average_score=candidate.average_score,
            max_score=candidate.max_score,
            repeated_count=candidate.repeated_count,
            latest_category=candidate.latest_category,
            momentum_evidence=candidate.momentum_evidence,
            dominant_blockers=candidate.blockers,
            warnings=candidate.warnings,
            reason=candidate.reason,
            trade_allowed=False,
            paper_trade_allowed=False,
            live_trade_allowed=False,
        )

    def _dominant_blockers(self, results: list[dict]) -> list[dict]:
        """Return dominant blockers from completed results."""
        counter: Counter = Counter()
        for result in results:
            signal = result.get("signal") or {}
            values = list(result.get("blockers") or []) + list(signal.get("blockers") or [])
            for value in values:
                text = str(value).strip()
                if text:
                    counter[text] += 1
        return [{"text": text, "count": count} for text, count in counter.most_common(5)]
