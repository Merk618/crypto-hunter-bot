"""Paper account state and accounting."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.trading_models import PaperFill, PaperOrder, PaperPosition
from app.portfolio.positions import update_market_price


@dataclass
class PaperAccount:
    """In-memory paper account with balances, positions, orders, fills, and PnL."""

    starting_cash: float = 10000.0
    cash_balance: float | None = None
    equity: float | None = None
    open_positions: dict[str, PaperPosition] = field(default_factory=dict)
    closed_positions: list[PaperPosition] = field(default_factory=list)
    orders: list[PaperOrder] = field(default_factory=list)
    fills: list[PaperFill] = field(default_factory=list)
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_fees_paid: float = 0.0

    def __post_init__(self) -> None:
        """Initialize cash and equity from starting cash."""
        if self.cash_balance is None:
            self.cash_balance = float(self.starting_cash)
        if self.equity is None:
            self.equity = float(self.starting_cash)

    def reset(self) -> None:
        """Reset account state back to starting cash."""
        self.cash_balance = float(self.starting_cash)
        self.equity = float(self.starting_cash)
        self.open_positions.clear()
        self.closed_positions.clear()
        self.orders.clear()
        self.fills.clear()
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.total_fees_paid = 0.0

    def mark_to_market(self, symbol_prices: dict[str, float]) -> None:
        """Update open position values from latest synthetic or public prices."""
        for symbol, price in symbol_prices.items():
            normalized = symbol.upper().replace("-", "/")
            position = self.open_positions.get(normalized)
            if position and price > 0:
                update_market_price(position, float(price))
        self._recalculate_equity()

    def _recalculate_equity(self) -> None:
        """Recalculate account equity and unrealized PnL."""
        self.unrealized_pnl = sum(position.unrealized_pnl for position in self.open_positions.values())
        market_value = sum(position.market_value for position in self.open_positions.values())
        self.equity = float(self.cash_balance or 0.0) + market_value

    def summary(self) -> dict:
        """Return a JSON-friendly account summary."""
        self._recalculate_equity()
        return {
            "starting_cash": self.starting_cash,
            "cash_balance": self.cash_balance,
            "equity": self.equity,
            "open_positions": len(self.open_positions),
            "closed_positions": len(self.closed_positions),
            "orders": len(self.orders),
            "fills": len(self.fills),
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_fees_paid": self.total_fees_paid,
        }
