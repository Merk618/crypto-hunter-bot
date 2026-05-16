"""Read-only options scanner models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

from app.config import get_settings


def _utc_now() -> str:
    """Return a UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OptionsScanRequest:
    """Options scanner request with safe default filters."""

    symbols: list[str] = field(default_factory=list)
    option_type: Literal["call", "put", "both"] | str = "call"
    min_volume: int | None = None
    min_open_interest: int | None = None
    max_spread_pct: float | None = None
    delta_min: float | None = None
    delta_max: float | None = None
    min_dte: int | None = None
    max_dte: int | None = None
    target_dte_min: int | None = None
    target_dte_max: int | None = None
    top_n: int | None = None
    include_rejected: bool = False

    def __post_init__(self) -> None:
        """Apply config defaults and normalize request values."""
        settings = get_settings()
        self.symbols = [symbol.strip().upper() for symbol in self.symbols if symbol and symbol.strip()]
        self.option_type = str(self.option_type or "call").lower()
        if self.option_type not in {"call", "put", "both"}:
            self.option_type = "call"
        self.min_volume = settings.options_scanner_min_volume if self.min_volume is None else self.min_volume
        self.min_open_interest = settings.options_scanner_min_open_interest if self.min_open_interest is None else self.min_open_interest
        self.max_spread_pct = settings.options_scanner_max_spread_pct if self.max_spread_pct is None else self.max_spread_pct
        self.delta_min = settings.options_scanner_target_delta_min if self.delta_min is None else self.delta_min
        self.delta_max = settings.options_scanner_target_delta_max if self.delta_max is None else self.delta_max
        self.min_dte = settings.options_scanner_min_dte if self.min_dte is None else self.min_dte
        self.max_dte = settings.options_scanner_max_dte if self.max_dte is None else self.max_dte
        self.target_dte_min = settings.options_scanner_target_dte_min if self.target_dte_min is None else self.target_dte_min
        self.target_dte_max = settings.options_scanner_target_dte_max if self.target_dte_max is None else self.target_dte_max
        self.top_n = settings.options_scanner_top_n if self.top_n is None else self.top_n

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class RankedOptionContract:
    """Read-only ranked option contract."""

    rank: int | None
    symbol: str
    underlying: str
    expiration: str | None
    dte: int | None
    strike: float | None
    option_type: str
    bid: float | None
    ask: float | None
    mid: float | None
    last: float | None
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    spread_pct: float | None
    liquidity_score: float
    contract_score: float
    underlying_score: float
    total_score: float
    label: str
    reasons: list[str]
    warnings: list[str]
    blockers: list[str]
    source: str = "stock_hunter_ranked_option_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class OptionsScanResult:
    """Read-only options scan result."""

    symbols_scanned: int
    contracts_analyzed: int
    candidates_found: int
    rejected_count: int
    top_candidates: list[dict]
    by_symbol: dict
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=_utc_now)
    source: str = "stock_hunter_options_scan_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
