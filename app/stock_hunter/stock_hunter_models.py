"""Models for the read-only Stock/Options Hunter skeleton."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass
class StockWatchlistItem:
    """In-memory stock watchlist item."""

    symbol: str
    name: str | None = None
    sector: str | None = None
    priority: int = 100
    enabled: bool = True
    notes: str | None = None

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class StockSignalResult:
    """Read-only stock signal placeholder result."""

    symbol: str
    score: int
    category: str
    reasons: list[str]
    warnings: list[str]
    blockers: list[str]
    latest_price: float | None
    trend_status: str
    volume_status: str
    source: str = "stock_hunter_signal_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class OptionContractSnapshot:
    """Read-only option contract snapshot."""

    symbol: str
    underlying: str
    expiration: str
    strike: float
    option_type: Literal["call", "put"] | str
    bid: float | None
    ask: float | None
    last: float | None
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    spread_pct: float | None = None
    liquidity_score: float = 0.0

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class OptionsChainAnalysis:
    """Read-only options chain analysis."""

    underlying: str
    contracts_analyzed: int
    best_call_candidates: list[dict]
    best_put_candidates: list[dict]
    rejected_contracts_count: int
    warnings: list[str] = field(default_factory=list)
    source: str = "stock_hunter_options_chain_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class StockScannerResult:
    """Read-only scanner result for one symbol."""

    symbol: str
    stock_signal: dict | None
    options_analysis: dict | None
    action: str
    notes: list[str]
    warnings: list[str]
    blockers: list[str]
    source: str = "stock_hunter_scanner_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
