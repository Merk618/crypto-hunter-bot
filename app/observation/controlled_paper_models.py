"""Controlled paper observation models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class ControlledPaperObservationStatus:
    """Controlled paper observation status."""

    enabled: bool
    approval_required: bool
    operator_start_required: bool
    buys_allowed: bool
    sells_allowed: bool
    max_notional_per_trade: float
    max_trades_per_run: int
    max_trades_per_day: int
    allowed_symbols: list[str]
    paper_trade_observation_enabled: bool
    live_trading_locked: bool
    source: str = "crypto_hunter_controlled_paper_observation_status_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ControlledPaperObservationRequest:
    """Controlled paper observation request."""

    manual_start: bool = False
    operator_acknowledged: bool = False
    allow_paper_trade_preview: bool = True
    allow_paper_trade_execution: bool = False
    symbols: list[str] = field(default_factory=list)
    timeframe: str = "1h"
    max_trades: int | None = None
    reason: str = "controlled paper observation"


@dataclass
class ControlledPaperObservationDecision:
    """Controlled paper observation gate decision."""

    allowed: bool
    status: str
    message: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    approval_gate_status: str | None = None
    fresh_validation_status: str | None = None
    paper_trade_readiness_status: str | None = None
    risk_hygiene_status: str | None = None
    source: str = "crypto_hunter_controlled_paper_observation_decision_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ControlledPaperTradePreview:
    """Controlled paper trade preview."""

    symbol: str
    side: str
    signal_score: float
    signal_category: str
    risk_approved: bool
    estimated_price: float
    requested_notional: float
    capped_notional: float
    estimated_quantity: float
    fees_estimate: float
    slippage_estimate: float
    allowed_for_execution: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source: str = "crypto_hunter_controlled_paper_trade_preview_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ControlledPaperObservationRun:
    """Controlled paper observation run."""

    run_id: str
    status: str
    started_at: str
    completed_at: str
    symbols_processed: int
    signals_generated: int
    risk_decisions_generated: int
    paper_trade_previews_created: int
    paper_trades_created: int
    blocked_trades: int
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    previews: list[dict] = field(default_factory=list)
    trade_results: list[dict] = field(default_factory=list)
    source: str = "crypto_hunter_controlled_paper_observation_run_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


def now_utc() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()
