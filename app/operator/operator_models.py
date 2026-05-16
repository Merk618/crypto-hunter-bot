"""Operator-facing status models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def _utc_now() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OperatorStatus:
    """Standalone backend operator status."""

    mode: str
    backend_healthy: bool
    live_trading_locked: bool
    kraken_status: dict
    moomoo_status: dict
    paper_status: dict
    journal_status: dict
    alerts_status: dict
    safety_audit_passed: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=_utc_now)
    source: str = "crypto_hunter_operator_status_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class StartupCheckResult:
    """Startup validation result."""

    passed: bool
    checks: dict
    warnings: list[str]
    blockers: list[str]
    recommended_actions: list[str]
    generated_at: str = field(default_factory=_utc_now)
    source: str = "crypto_hunter_startup_check_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class CommandSummary:
    """Safe local command summary."""

    title: str
    commands: list[dict]
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source: str = "crypto_hunter_command_summary_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
