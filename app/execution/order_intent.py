"""Order intent and validation models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def _json(value: Any) -> Any:
    """Convert nested values to JSON-friendly values."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


@dataclass
class OrderIntent:
    """Order intent for future execution validation."""

    symbol: str
    side: Literal["buy", "sell"] | str
    order_type: Literal["market"] | str
    quantity: float
    estimated_price: float
    reason: str
    signal_score: int
    signal_category: str
    risk_approved: bool
    risk_decision_id: str | None = None
    intent_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "crypto_hunter_order_intent_v1"

    @property
    def estimated_notional(self) -> float:
        """Calculate estimated notional."""
        return float(self.quantity) * float(self.estimated_price)

    def to_dict(self) -> dict:
        """Return JSON-friendly dict."""
        data = _json(asdict(self))
        data["estimated_notional"] = self.estimated_notional
        return data


@dataclass
class OrderValidationResult:
    """Order validation result."""

    approved: bool
    intent_id: str
    symbol: str
    side: str
    normalized_symbol: str
    approved_quantity: float | None
    estimated_price: float
    estimated_notional: float
    blockers: list[str]
    warnings: list[str]
    checks: dict
    source: str = "crypto_hunter_order_validation_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly dict."""
        return _json(asdict(self))
