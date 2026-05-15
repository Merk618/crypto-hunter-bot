"""Backtesting dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _json(value: Any) -> Any:
    """Convert nested dataclass values to JSON-friendly structures."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest configuration."""

    starting_cash: float = 10000.0
    fee_rate: float = 0.0025
    slippage_bps: float = 10.0
    timeframe: str = "1h"
    min_signal_score: int = 80
    allow_shorts: bool = False
    max_open_positions: int = 3


@dataclass
class BacktestTrade:
    """Completed backtest trade."""

    trade_id: str
    symbol: str
    side: str
    entry_time: Any
    exit_time: Any
    entry_price: float
    exit_price: float
    quantity: float
    entry_fee: float
    exit_fee: float
    gross_pnl: float
    net_pnl: float
    return_pct: float
    exit_reason: str
    signal_score: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Return JSON-friendly dict."""
        return _json(asdict(self))


@dataclass
class BacktestEquityPoint:
    """Backtest equity curve point."""

    timestamp: Any
    cash: float
    equity: float
    open_position_value: float
    realized_pnl: float
    unrealized_pnl: float
    drawdown_pct: float

    def to_dict(self) -> dict:
        """Return JSON-friendly dict."""
        return _json(asdict(self))


@dataclass
class BacktestResult:
    """Backtest result summary."""

    symbol: str
    timeframe: str
    starting_cash: float
    ending_cash: float
    ending_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    total_fees: float
    trades: list[BacktestTrade]
    equity_curve: list[BacktestEquityPoint]
    warnings: list[str]
    source: str = "crypto_hunter_backtest_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly dict."""
        return _json(asdict(self))
