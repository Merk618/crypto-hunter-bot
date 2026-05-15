"""Exchange adapter interface tests."""

import pytest

from app.config import Settings
from app.exchanges.base import BaseExchange
from app.exchanges.kraken_adapter import KrakenAdapter


def test_base_exchange_cannot_be_instantiated_directly() -> None:
    """BaseExchange is abstract and cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseExchange()


def test_kraken_adapter_implements_required_interface_methods() -> None:
    """KrakenAdapter must provide all BaseExchange methods."""
    adapter = KrakenAdapter(settings=Settings(_env_file=None))
    required_methods = [
        "get_symbols",
        "get_candles",
        "get_ticker",
        "get_orderbook",
        "get_balance",
        "place_order",
        "cancel_order",
        "get_open_orders",
        "get_positions",
        "normalize_symbol",
    ]
    for method_name in required_methods:
        assert callable(getattr(adapter, method_name))
