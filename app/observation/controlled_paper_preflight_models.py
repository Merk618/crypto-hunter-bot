"""Controlled paper activation preflight models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class ControlledPaperPreflightCheck:
    """One preflight check."""

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
class ControlledPaperPreflightReport:
    """Controlled paper preflight report."""

    preflight_status: str
    activation_eligible: bool
    config_change_required: bool
    controlled_paper_enabled_now: bool
    buys_allowed_now: bool
    sells_allowed_now: bool
    paper_trade_execution_allowed_now: bool
    live_review_allowed: bool
    audit_passed: bool
    review_clean: bool
    fresh_validation_passed: bool
    current_risk_clean: bool
    legacy_warnings_present: bool
    approval_gate_status: str
    paper_trade_readiness_status: str
    completed_runs_analyzed: int
    observations_analyzed: int
    strong_buy_count: int
    risk_approved_count: int
    checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_controlled_paper_preflight_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ControlledPaperActivationPlan:
    """Read-only activation plan."""

    activation_eligible: bool
    current_mode: str
    required_manual_steps: list[str]
    required_config_flags: dict
    flags_that_must_remain_false: dict
    max_notional_per_trade: float
    max_trades_per_run: int
    max_trades_per_day: int
    safety_warnings: list[str]
    rollback_steps: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_controlled_paper_activation_plan_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ControlledPaperPreflightPackage:
    """Complete preflight package."""

    preflight_report: dict
    activation_plan: dict
    audit_summary: dict
    review_summary: dict
    approval_summary: dict
    readiness_summary: dict
    fresh_validation_summary: dict
    risk_hygiene_summary: dict
    final_recommendation: str
    source: str = "crypto_hunter_controlled_paper_preflight_package_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
