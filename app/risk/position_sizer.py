"""Position sizing helpers."""


class PositionSizingError(ValueError):
    """Raised when position sizing inputs are invalid."""


class PositionSizer:
    """Calculate and cap trade quantities from risk constraints."""

    def calculate_quantity_by_risk(self, equity: float, entry_price: float, stop_loss_price: float, max_risk_per_trade: float) -> float:
        """Calculate quantity from account risk and per-unit price risk."""
        if equity <= 0:
            raise PositionSizingError("Equity must be greater than zero")
        if entry_price <= 0:
            raise PositionSizingError("Entry price must be greater than zero")
        if stop_loss_price <= 0:
            raise PositionSizingError("Stop loss price must be greater than zero")
        if max_risk_per_trade <= 0 or max_risk_per_trade > 0.05:
            raise PositionSizingError("Max risk per trade must be > 0 and <= 0.05")
        risk_per_unit = abs(entry_price - stop_loss_price)
        if risk_per_unit <= 0:
            raise PositionSizingError("Risk per unit must be greater than zero")
        risk_amount = equity * max_risk_per_trade
        return risk_amount / risk_per_unit

    def cap_quantity_by_cash(self, quantity: float, cash_balance: float, entry_price: float, fee_rate: float) -> float:
        """Cap quantity by available cash including fees."""
        if quantity <= 0 or cash_balance <= 0 or entry_price <= 0:
            return 0.0
        affordable = cash_balance / (entry_price * (1 + max(fee_rate, 0)))
        return min(quantity, affordable)

    def cap_quantity_by_allocation(self, quantity: float, equity: float, entry_price: float, max_allocation: float) -> float:
        """Cap quantity by maximum single-position allocation."""
        if quantity <= 0 or equity <= 0 or entry_price <= 0 or max_allocation <= 0:
            return 0.0
        allocation_quantity = (equity * max_allocation) / entry_price
        return min(quantity, allocation_quantity)

    def round_quantity(self, quantity: float, decimals: int = 8) -> float:
        """Round a quantity to exchange-style precision."""
        return round(max(quantity, 0.0), decimals)
