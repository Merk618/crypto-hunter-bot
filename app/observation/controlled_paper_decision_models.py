"""Controlled paper preflight review and decision models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class ControlledPaperDecisionCheck:
    """One controlled paper decision check."""

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
class ControlledPaperObservationDecisionReport:
    """Operator-facing controlled paper observation decision."""

    decision: str
    confidence: str
    allow_config_review: bool
    allow_paper_activation: bool
    allow_live_review: bool
    current_mode: str
    preflight_status: str
    activation_eligible: bool
    approval_gate_status: str
    paper_trade_readiness_status: str
    fresh_validation_status: str
    controlled_paper_audit_passed: bool
    controlled_paper_review_clean: bool
    current_risk_clean: bool
    legacy_warnings_present: bool
    completed_runs_analyzed: int
    observations_analyzed: int
    strong_buy_count: int
    risk_approved_count: int
    early_recovery_count: int
    controlled_paper_enabled_now: bool
    buys_allowed_now: bool
    sells_allowed_now: bool
    paper_trade_execution_allowed_now: bool
    checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_controlled_paper_decision_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ControlledPaperDecisionPackage:
    """Complete controlled paper review package."""

    decision_report: dict
    preflight_summary: dict
    activation_plan_summary: dict
    audit_summary: dict
    review_summary: dict
    approval_summary: dict
    readiness_summary: dict
    fresh_validation_summary: dict
    risk_hygiene_summary: dict
    observation_summary: dict
    final_recommendation: str
    source: str = "crypto_hunter_controlled_paper_decision_package_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
