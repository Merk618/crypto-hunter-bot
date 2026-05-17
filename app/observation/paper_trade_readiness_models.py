"""Paper trade observation readiness models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class PaperTradeReadinessCheck:
    """One readiness check."""

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
class PaperTradeReadinessReport:
    """Paper trade observation readiness report."""

    ready: bool
    decision: str
    confidence: str
    completed_runs_analyzed: int
    observations_analyzed: int
    strong_buy_count: int
    risk_approved_count: int
    early_recovery_count: int
    risk_record_inconsistencies: int
    safety_audit_passed: bool
    live_trading_locked: bool
    add_order_absent: bool
    paper_trade_observation_allowed_now: bool = False
    operator_approval_required: bool = True
    checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_paper_trade_readiness_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)

