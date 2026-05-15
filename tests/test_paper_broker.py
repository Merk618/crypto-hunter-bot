"""Paper broker simulation tests."""

import pytest

from app.config import Settings
from app.execution.paper_broker import PaperBroker
from app.portfolio.paper_account import PaperAccount


def broker(starting_cash: float = 10000.0) -> PaperBroker:
    """Create a deterministic paper broker."""
    settings = Settings(_env_file=None, PAPER_STARTING_CASH=starting_cash, PAPER_FEE_RATE=0.0025, PAPER_SLIPPAGE_BPS=10)
    return PaperBroker(account=PaperAccount(starting_cash=starting_cash), settings=settings)


def test_buy_market_order_reduces_cash() -> None:
    """Buy orders reduce cash by notional plus fee."""
    b = broker()
    result = b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    assert result.accepted is True
    assert b.account.cash_balance < 10000


def test_buy_market_order_creates_position() -> None:
    """Buy orders create positions."""
    b = broker()
    b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    assert b.get_position("BTC/USD") is not None


def test_buy_market_order_applies_fee() -> None:
    """Buy orders track fees."""
    b = broker()
    result = b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    assert result.fill is not None
    expected_fill_price = 10000 * 1.001
    expected_fee = expected_fill_price * 0.1 * 0.0025
    assert result.fill.fee == pytest.approx(expected_fee)
    assert b.account.total_fees_paid == pytest.approx(expected_fee)


def test_buy_market_order_applies_slippage() -> None:
    """Buy fill price includes positive slippage."""
    b = broker()
    result = b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    assert result.fill is not None
    assert result.fill.price == pytest.approx(10010.0)
    assert result.fill.slippage == pytest.approx(10.0)


def test_buying_more_than_cash_allows_is_rejected() -> None:
    """Broker rejects unaffordable buys."""
    result = broker(starting_cash=100).place_market_order("BTC/USD", "buy", 1.0, 10000)
    assert result.accepted is False
    assert "Insufficient" in result.message


def test_zero_quantity_is_rejected() -> None:
    """Broker rejects zero quantity."""
    result = broker().place_market_order("BTC/USD", "buy", 0.0, 10000)
    assert result.accepted is False
    assert "Quantity" in result.message


def test_negative_market_price_is_rejected() -> None:
    """Broker rejects negative market price."""
    result = broker().place_market_order("BTC/USD", "buy", 0.1, -1)
    assert result.accepted is False
    assert "Market price" in result.message


def test_sell_order_reduces_position_quantity() -> None:
    """Partial sells reduce quantity."""
    b = broker()
    b.place_market_order("BTC/USD", "buy", 0.2, 10000)
    b.place_market_order("BTC/USD", "sell", 0.1, 11000)
    position = b.account.open_positions["BTC/USD"]
    assert position.quantity == pytest.approx(0.1)


def test_selling_more_than_held_quantity_is_rejected() -> None:
    """Broker rejects overselling."""
    b = broker()
    b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    result = b.place_market_order("BTC/USD", "sell", 0.2, 11000)
    assert result.accepted is False
    assert "Cannot sell more" in result.message


def test_full_sell_closes_position() -> None:
    """Full sells close positions."""
    b = broker()
    b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    result = b.place_market_order("BTC/USD", "sell", 0.1, 11000)
    assert result.accepted is True
    assert "BTC/USD" not in b.account.open_positions
    assert len(b.account.closed_positions) == 1


def test_realized_pnl_is_calculated_on_sell() -> None:
    """Sells calculate realized PnL."""
    b = broker()
    b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    b.place_market_order("BTC/USD", "sell", 0.1, 11000)
    assert b.account.realized_pnl > 0


def test_mark_to_market_updates_unrealized_pnl() -> None:
    """Mark-to-market updates unrealized PnL."""
    b = broker()
    b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    b.mark_to_market({"BTC/USD": 12000})
    assert b.account.unrealized_pnl > 0


def test_close_position_closes_an_open_position() -> None:
    """close_position closes the full position."""
    b = broker()
    b.place_market_order("BTC/USD", "buy", 0.1, 10000)
    result = b.close_position("BTC-USD", 11000)
    assert result.accepted is True
    assert b.get_position("BTC/USD") is None
