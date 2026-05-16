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
    """Read-only quote snapshot placeholder."""

    symbol: str
    available: bool
    message: str
    last_price: float | None = None
    bid: float | None = None
    ask: float | None = None
    timestamp: str = field(default_factory=_utc_now)
    source: str = "moomoo_readonly_quote_snapshot_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass(frozen=True)
class MooMooCandle:
    """Read-only candle placeholder."""

    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str = "moomoo_readonly_candle_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass(frozen=True)
class MooMooOptionContract:
    """Read-only option contract placeholder."""

    symbol: str
    underlying: str
    expiration: str | None
    strike: float | None
    option_type: str | None
    source: str = "moomoo_readonly_option_contract_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
