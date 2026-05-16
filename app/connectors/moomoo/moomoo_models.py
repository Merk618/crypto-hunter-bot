"""Models for MooMoo read-only feasibility responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def _utc_now() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MooMooHealthStatus:
    """MooMoo package and OpenD health status."""

    enabled: bool
    configured: bool
    import_available: bool
    connected: bool
    host: str
    port: int
    read_only: bool
    trading_enabled: bool
    paper_trading_enabled: bool
    unlock_trade_context: bool
    warnings: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=_utc_now)
    source: str = "moomoo_readonly_health_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass(frozen=True)
class MooMooCapabilityReport:
    """Read-only capability report for future Stock/Options Hunter work."""

    stocks_market_data: bool = True
    etf_market_data: bool = True
    options_chain_data: bool = True
    historical_candles: bool = True
    watchlists: bool = True
    stock_filtering: bool = True
    paper_trading_future: bool = True
    live_trading_future_locked: bool = True
    read_only_now: bool = True
    source: str = "moomoo_readonly_capabilities_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass(frozen=True)
class MooMooQuoteSnapshot:
    """Read-only quote snapshot."""

    symbol: str
    available: bool
    message: str
    provider_symbol: str | None = None
    latest_price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    volume: float | None = None
    turnover: float | None = None
    bid: float | None = None
    ask: float | None = None
    timestamp: str = field(default_factory=_utc_now)
    source: str = "moomoo_readonly_quote"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass(frozen=True)
class MooMooCandle:
    """Read-only candle."""

    symbol: str
    provider_symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float | None = None
    source: str = "moomoo_readonly_candles"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass(frozen=True)
class MooMooOptionContract:
    """Read-only normalized option contract."""

    symbol: str
    underlying: str
    expiration: str | None
    strike: float | None
    option_type: str | None
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    spread_pct: float | None = None
    liquidity_score: float = 0.0
    source: str = "moomoo_readonly_option_contract_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
