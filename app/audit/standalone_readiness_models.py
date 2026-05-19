"""Standalone readiness audit models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class StandaloneReadinessAuditReport:
    """Standalone backend readiness audit."""

    ready_for_v1_freeze: bool
    readiness_status: str
    safety_audit_passed: bool
    live_trading_locked: bool
    add_order_absent: bool
    real_execution_absent: bool
    paper_trading_disabled: bool
    controlled_paper_disabled: bool
    observation_persistence_available: bool
    strategy_checkpoint_available: bool
    reporting_available: bool
    operator_layer_available: bool
    docs_available: bool
    test_suite_expected_minimum: int
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_standalone_readiness_audit_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class FinalSafetyReviewReport:
    """Final standalone safety review."""

    passed: bool
    live_trading_locked: bool
    add_order_absent: bool
    private_order_methods_absent: bool
    withdrawal_methods_absent: bool
    moomoo_execution_absent: bool
    paper_only_paths_labeled: bool
    secrets_not_exposed: bool
    dangerous_config_detected: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_final_safety_review_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class V1CompletionChecklist:
    """Crypto Hunter v1 completion checklist."""

    complete: bool
    items: list[dict] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    recommended_finish_steps: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_v1_completion_checklist_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
