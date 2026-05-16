"""Alert report models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4


def _utc_now() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AlertCandidate:
    """Normalized alert candidate for crypto, stock, or option research."""

    asset_class: Literal["crypto", "stock", "option"] | str
    symbol: str
    title: str
    score: float
    category: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source: str = "yucatanatrades_alert_candidate_v1"
    risk_level: str | None = None

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class AlertReport:
    """Aggregated alert report."""

    title: str
    crypto_candidates: list[dict]
    stock_candidates: list[dict]
    option_candidates: list[dict]
    risk_summary: dict
    safety_summary: dict
    warnings: list[str] = field(default_factory=list)
    report_id: str = field(default_factory=lambda: str(uuid4()))
    generated_at: str = field(default_factory=_utc_now)
    source: str = "yucatanatrades_alert_report_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class AlertSendResult:
    """Alert send or dry-run result."""

    channel: str
    attempted: bool
    sent: bool
    message: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
