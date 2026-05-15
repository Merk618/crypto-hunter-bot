"""Paper trading models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal


OrderSide = Literal["buy", "sell"]
OrderType = Literal["market"]


def _jsonify(value: Any) -> Any:
    """Convert dataclass values into JSON-friendly primitives."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonify(item) for key, item in value.items()}
    return value


@dataclass
class SerializableModel:
    """Mixin for dataclass models returned by FastAPI routes."""

    def to_dict(self) -> dict:
        """Return JSON-friendly dictionary output."""
        return _jsonify(asdict(self))


@dataclass
class PaperOrder(SerializableModel):
    """Paper order record."""

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    requested_price: float
    simulated_fill_price: float | None
    status: str
    created_at: datetime
    filled_at: datetime | None
    reason: str | None = None


@dataclass
class PaperFill(SerializableModel):
    """Paper fill record."""

    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float
    slippage: float
    timestamp: datetime


@dataclass
class PaperPosition(SerializableModel):
    """Open or closed paper position."""

    symbol: str
    quantity: float
    average_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    opened_at: datetime
    updated_at: datetime
    fee_basis: float = 0.0


@dataclass
class PaperTradeResult(SerializableModel):
    """Result from a paper trade simulation."""

    accepted: bool
    order: PaperOrder | None
    fill: PaperFill | None
    position: PaperPosition | None
    message: str
    warnings: list[str] = field(default_factory=list)
