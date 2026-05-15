"""Live trading lock tests."""

import pytest

from app.config import Settings
from app.execution.live_broker import LiveBroker, LiveTradingDisabledError
from app.exchanges.kraken_adapter import KrakenAdapter


def test_live_broker_refuses_orders_by_default() -> None:
    """LiveBroker must reject orders with default settings."""
    settings = Settings(_env_file=None)
    exchange = KrakenAdapter(settings=settings)
    broker = LiveBroker(exchange=exchange, settings=settings)

    with pytest.raises(LiveTradingDisabledError):
        broker.place_order("BTC/USD", "buy", "market", 0.01)
