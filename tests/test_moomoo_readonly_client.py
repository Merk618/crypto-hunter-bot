"""MooMoo read-only client tests."""

import inspect

from app.config import Settings
from app.connectors.moomoo.moomoo_health import MooMooHealth
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient


def client() -> MooMooReadOnlyClient:
    """Build a read-only client with deterministic unavailable health."""
    settings = Settings(_env_file=None)
    health = MooMooHealth(settings, import_checker=lambda _: False)
    return MooMooReadOnlyClient(settings=settings, health_checker=health)


def test_readonly_client_exposes_capabilities() -> None:
    """Capabilities describe planned read-only market data."""
    capabilities = client().get_supported_capabilities().to_dict()

    assert capabilities["stocks_market_data"] is True
    assert capabilities["options_chain_data"] is True
    assert capabilities["live_trading_future_locked"] is True
    assert capabilities["read_only_now"] is True


def test_readonly_client_has_no_order_placement_methods() -> None:
    """Client does not expose order placement surfaces."""
    names = {name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient)}

    assert not any(name in names for name in {"place_order", "submit_order", "buy", "sell"})


def test_readonly_client_has_no_cancel_order_methods() -> None:
    """Client does not expose cancel order surfaces."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "cancel" not in names


def test_readonly_client_has_no_unlock_trade_context_method() -> None:
    """Client does not expose trade-context unlock."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "unlock" not in names


def test_readonly_client_returns_clean_unavailable_quote() -> None:
    """Missing package/OpenD returns unavailable placeholder."""
    quote = client().get_quote_snapshot("AAPL")

    assert quote["available"] is False
    assert quote["symbol"] == "AAPL"
