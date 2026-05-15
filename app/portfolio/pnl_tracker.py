"""PnL helper calculations."""


def realized_pnl_for_sale(entry_price: float, exit_price: float, quantity: float, allocated_entry_fee: float, exit_fee: float) -> float:
    """Calculate realized PnL net of allocated entry and exit fees."""
    return ((exit_price - entry_price) * quantity) - allocated_entry_fee - exit_fee


def unrealized_pnl_for_position(entry_price: float, current_price: float, quantity: float, fee_basis: float = 0.0) -> float:
    """Calculate unrealized PnL net of remaining entry fee basis."""
    return ((current_price - entry_price) * quantity) - fee_basis
