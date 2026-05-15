"""In-memory paper trading broker."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class PaperBroker:
    """Simple paper broker for Phase 1 simulations."""

    orders: list[dict] = field(default_factory=list)

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Record a simulated order and return it."""
        order = {
            "id": str(uuid4()),
            "symbol": symbol,
            "side": side.lower(),
            "order_type": order_type.lower(),
            "quantity": quantity,
            "price": price,
            "status": "paper_filled",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.orders.append(order)
        return order

    def get_open_orders(self) -> list[dict]:
        """Return open paper orders."""
        return [order for order in self.orders if order["status"] == "open"]
