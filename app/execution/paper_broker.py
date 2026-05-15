"""Safe in-memory paper trading broker."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings, get_settings
from app.models.trading_models import PaperFill, PaperOrder, PaperPosition, PaperTradeResult
from app.portfolio.paper_account import PaperAccount
from app.portfolio.pnl_tracker import realized_pnl_for_sale
from app.portfolio.positions import create_position, update_market_price


class PaperBrokerError(ValueError):
    """Raised for invalid paper trading requests."""


class PaperBroker:
    """Simulate market orders, balances, positions, fees, slippage, and PnL."""

    def __init__(self, account: PaperAccount | None = None, settings: Settings | None = None) -> None:
        """Initialize the broker with a paper account and settings."""
        self.settings = settings or get_settings()
        self.account = account or PaperAccount(starting_cash=self.settings.paper_starting_cash)
        self.fee_rate = float(self.settings.paper_fee_rate)
        self.slippage_bps = float(self.settings.paper_slippage_bps)

    def get_account_summary(self) -> dict:
        """Return paper account summary."""
        return self.account.summary()

    def get_positions(self) -> list[dict]:
        """Return open paper positions."""
        return [position.to_dict() for position in self.account.open_positions.values()]

    def get_position(self, symbol: str) -> dict | None:
        """Return one open paper position."""
        position = self.account.open_positions.get(self._normalize_symbol(symbol))
        return position.to_dict() if position else None

    def get_orders(self) -> list[dict]:
        """Return all paper orders."""
        return [order.to_dict() for order in self.account.orders]

    def get_fills(self) -> list[dict]:
        """Return all paper fills."""
        return [fill.to_dict() for fill in self.account.fills]

    def place_market_order(self, symbol: str, side: str, quantity: float, market_price: float, reason: str | None = None) -> PaperTradeResult:
        """Simulate a paper market order."""
        normalized_symbol = self._normalize_symbol(symbol)
        side = side.lower().strip()
        warnings: list[str] = []
        error = self._validate_market_order(normalized_symbol, side, quantity, market_price)
        if error:
            return PaperTradeResult(False, None, None, self.account.open_positions.get(normalized_symbol), error, warnings)

        fill_price = self._fill_price(side, market_price)
        slippage = abs(fill_price - market_price)
        notional = quantity * fill_price
        fee = notional * self.fee_rate

        if side == "buy" and self.account.cash_balance is not None and self.account.cash_balance < notional + fee:
            return PaperTradeResult(False, None, None, None, "Insufficient paper cash for buy order", warnings)
        if side == "sell":
            position = self.account.open_positions.get(normalized_symbol)
            if position is None:
                return PaperTradeResult(False, None, None, None, "No open paper position to sell", warnings)
            if quantity > position.quantity:
                return PaperTradeResult(False, None, None, position, "Cannot sell more than current paper position quantity", warnings)

        now = datetime.now(timezone.utc)
        order = PaperOrder(
            order_id=str(uuid4()),
            symbol=normalized_symbol,
            side=side,  # type: ignore[arg-type]
            order_type="market",
            quantity=float(quantity),
            requested_price=float(market_price),
            simulated_fill_price=float(fill_price),
            status="filled",
            created_at=now,
            filled_at=now,
            reason=reason,
        )
        fill = PaperFill(
            fill_id=str(uuid4()),
            order_id=order.order_id,
            symbol=normalized_symbol,
            side=side,  # type: ignore[arg-type]
            quantity=float(quantity),
            price=float(fill_price),
            fee=float(fee),
            slippage=float(slippage),
            timestamp=now,
        )
        self.account.orders.append(order)
        self.account.fills.append(fill)
        self.account.total_fees_paid += fee

        if side == "buy":
            position = self._apply_buy(normalized_symbol, quantity, fill_price, fee)
            message = "Paper buy filled"
        else:
            position = self._apply_sell(normalized_symbol, quantity, fill_price, fee)
            message = "Paper sell filled"

        self.account.mark_to_market({normalized_symbol: market_price})
        return PaperTradeResult(True, order, fill, position, message, warnings)

    def close_position(self, symbol: str, market_price: float, reason: str | None = None) -> PaperTradeResult:
        """Close an open paper position at a synthetic market price."""
        normalized_symbol = self._normalize_symbol(symbol)
        position = self.account.open_positions.get(normalized_symbol)
        if position is None:
            return PaperTradeResult(False, None, None, None, "No open paper position to close", [])
        return self.place_market_order(normalized_symbol, "sell", position.quantity, market_price, reason)

    def mark_to_market(self, symbol_prices: dict[str, float]) -> dict:
        """Update paper account unrealized PnL from prices."""
        self.account.mark_to_market(symbol_prices)
        return self.account.summary()

    def reset(self) -> dict:
        """Reset the paper account."""
        self.account.reset()
        return self.account.summary()

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Backward-compatible paper order method for market orders."""
        if order_type.lower() != "market":
            result = PaperTradeResult(False, None, None, None, "Only market paper orders are supported", [])
        elif price is None:
            result = PaperTradeResult(False, None, None, None, "Market price is required for paper orders", [])
        else:
            result = self.place_market_order(symbol, side, quantity, price)
        return result.to_dict()

    def _apply_buy(self, symbol: str, quantity: float, fill_price: float, fee: float) -> PaperPosition:
        """Apply a buy fill to cash and positions."""
        notional = quantity * fill_price
        self.account.cash_balance = float(self.account.cash_balance or 0.0) - notional - fee
        existing = self.account.open_positions.get(symbol)
        if existing is None:
            position = create_position(symbol, quantity, fill_price, fee)
            self.account.open_positions[symbol] = position
            return position

        old_cost = existing.average_entry_price * existing.quantity
        new_cost = fill_price * quantity
        new_quantity = existing.quantity + quantity
        existing.average_entry_price = (old_cost + new_cost) / new_quantity
        existing.quantity = new_quantity
        existing.fee_basis += fee
        return update_market_price(existing, fill_price)

    def _apply_sell(self, symbol: str, quantity: float, fill_price: float, fee: float) -> PaperPosition | None:
        """Apply a sell fill to cash, positions, and realized PnL."""
        position = self.account.open_positions[symbol]
        notional = quantity * fill_price
        self.account.cash_balance = float(self.account.cash_balance or 0.0) + notional - fee

        fee_ratio = quantity / position.quantity
        allocated_entry_fee = position.fee_basis * fee_ratio
        realized = realized_pnl_for_sale(position.average_entry_price, fill_price, quantity, allocated_entry_fee, fee)
        self.account.realized_pnl += realized
        position.realized_pnl += realized
        position.fee_basis -= allocated_entry_fee
        position.quantity -= quantity

        if position.quantity <= 1e-12:
            closed = self.account.open_positions.pop(symbol)
            closed.quantity = 0.0
            closed.current_price = fill_price
            closed.market_value = 0.0
            closed.unrealized_pnl = 0.0
            closed.updated_at = datetime.now(timezone.utc)
            self.account.closed_positions.append(closed)
            return None

        return update_market_price(position, fill_price)

    def _validate_market_order(self, symbol: str, side: str, quantity: float, market_price: float) -> str | None:
        """Return an error message when a paper market order is invalid."""
        if side not in {"buy", "sell"}:
            return "Side must be buy or sell"
        if quantity <= 0:
            return "Quantity must be greater than zero"
        if market_price <= 0:
            return "Market price must be greater than zero"
        if not symbol:
            return "Symbol is required"
        return None

    def _fill_price(self, side: str, market_price: float) -> float:
        """Calculate simulated fill price with slippage."""
        slip = self.slippage_bps / 10000
        if side == "buy":
            return market_price * (1 + slip)
        return market_price * (1 - slip)

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize BTC-USD path symbols to BTC/USD."""
        return symbol.strip().upper().replace("-", "/")
