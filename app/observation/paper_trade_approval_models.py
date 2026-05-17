"""Paper-trade observation approval gate models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class PaperTradeApprovalCheck:
    """One paper-trade approval gate check."""

    name: str
    passed: bool
    status: str
    message: str
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class PaperTradeApprovalReport:
    """Paper-trade observation approval report."""

    approval_status: str
    eligible_for_operator_review: bool
    approved_for_paper_trade_observation: bool
    paper_trade_observation_enabled: bool
    completed_runs_analyzed: int
    observations_analyzed: int
    strong_buy_count: int
    risk_approved_count: int
    fresh_validation_passed: bool
    current_risk_clean: bool
    legacy_warnings_present: bool
    safety_audit_passed: bool
    live_trading_locked: bool
    add_order_absent: bool
    operator_approval_required: bool
    checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_paper_trade_approval_gate_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
