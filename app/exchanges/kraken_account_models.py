"""Kraken read-only account models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _json(value: Any) -> Any:
    """Convert nested model values to JSON-friendly values."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


@dataclass
class ExchangeBalance:
    """Read-only exchange balance."""

    asset: str
    balance: float
    available: float | None = None
    hold: float | None = None
    credit: float | None = None
    credit_used: float | None = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _json(asdict(self))


@dataclass
class ExchangeAccountSummary:
    """Read-only account summary."""

    exchange: str
    private_read_enabled: bool
    configured: bool
    balances: list[ExchangeBalance]
    total_assets_count: int
    nonzero_assets_count: int
    warnings: list[str]
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "kraken_private_read_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _json(asdict(self))
