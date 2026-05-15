"""Position helpers."""

from datetime import datetime, timezone

from app.models.trading_models import PaperPosition
from app.portfolio.pnl_tracker import unrealized_pnl_for_position


def create_position(symbol: str, quantity: float, fill_price: float, fee: float) -> PaperPosition:
    """Create a new paper position from a buy fill."""
    now = datetime.now(timezone.utc)
    return PaperPosition(
        symbol=symbol,
        quantity=quantity,
        average_entry_price=fill_price,
        current_price=fill_price,
        market_value=quantity * fill_price,
        unrealized_pnl=unrealized_pnl_for_position(fill_price, fill_price, quantity, fee),
        realized_pnl=0.0,
        opened_at=now,
        updated_at=now,
        fee_basis=fee,
    )


def update_market_price(position: PaperPosition, market_price: float) -> PaperPosition:
    """Update mark-to-market fields for a position."""
    position.current_price = market_price
    position.market_value = position.quantity * market_price
    position.unrealized_pnl = unrealized_pnl_for_position(position.average_entry_price, market_price, position.quantity, position.fee_basis)
    position.updated_at = datetime.now(timezone.utc)
    return position
