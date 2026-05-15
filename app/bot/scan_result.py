"""Scan result model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _to_dict(value: Any) -> Any:
    """Convert nested results to JSON-friendly values."""
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_dict(item) for key, item in value.items()}
    return value


@dataclass
class ScanResult:
    """Result for one scanned symbol."""

    symbol: str
    signal: Any = None
    risk_decision: Any = None
    trade_result: Any = None
    action_taken: str = "none"
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return _to_dict(asdict(self))
