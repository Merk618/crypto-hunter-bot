"""Models for read-only real-data validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def _utc_now() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ValidationCheck:
    """One validation check."""

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
class RealDataValidationReport:
    """Aggregated real-data validation report."""

    passed: bool
    generated_at: str
    safety_audit_passed: bool
    kraken_public_passed: bool
    moomoo_readonly_passed: bool
    crypto_signal_passed: bool
    stock_hunter_passed: bool
    options_scanner_passed: bool
    alerts_reporting_passed: bool
    operator_passed: bool
    checks: list[dict]
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    source: str = "crypto_hunter_real_data_validation_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
