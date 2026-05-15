"""Reporting dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _json(value: Any) -> Any:
    """Convert nested reporting values to JSON-friendly values."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


@dataclass
class ReportModel:
    """Base report model with JSON-friendly output."""

    def to_dict(self) -> dict:
        """Return a JSON-friendly dictionary."""
        return _json(asdict(self))


@dataclass
class DashboardOverview(ReportModel):
    """Dashboard overview report."""

    bot_status: dict
    mode: str
    is_running: bool
    is_paused: bool
    paper_equity: float
    paper_cash: float
    open_positions_count: int
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_fees_paid: float
    signals_today: int
    trades_today: int
    risk_status: dict
    kill_switch_active: bool
    last_scan_at: Any
    last_error: str | None
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PaperPerformanceReport(ReportModel):
    """Paper performance report."""

    starting_cash: float
    current_equity: float
    cash_balance: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    total_fees_paid: float
    open_positions: int
    closed_positions: int
    total_orders: int
    total_fills: int
    win_rate_if_available: float | None
    profit_factor_if_available: float | None
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SignalPerformanceReport(ReportModel):
    """Signal performance report."""

    total_signals: int
    strong_buy_count: int
    buy_watch_count: int
    neutral_count: int
    weak_count: int
    avoid_sell_count: int
    average_score: float
    symbols_ranked_by_latest_score: list[dict]
    recent_signals: list[dict]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RiskSummaryReport(ReportModel):
    """Risk summary report."""

    kill_switch_active: bool
    max_risk_per_trade: float
    max_daily_loss: float
    max_open_positions: int
    max_position_allocation: float
    min_signal_score_to_trade: int
    active_cooldowns: list[dict]
    recent_risk_rejections: list[dict]
    recent_blockers: list[str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RecentActivityReport(ReportModel):
    """Recent activity report."""

    recent_events: list[dict]
    recent_orders: list[dict]
    recent_fills: list[dict]
    recent_signals: list[dict]
    recent_errors: list[dict]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EquityCurveReport(ReportModel):
    """Equity curve report."""

    points: list[dict]
    starting_equity: float
    ending_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
