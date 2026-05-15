"""Kraken private read-only client tests."""

import base64

import pytest

from app.config import Settings
from app.exchanges.kraken_private_client import KrakenPrivateClient, KrakenPrivateDisabledError


def secret() -> str:
    """Return valid base64 fake secret."""
    return base64.b64encode(b"secret").decode("utf-8")


def settings(**overrides) -> Settings:
    """Build settings."""
    base = {"KRAKEN_PRIVATE_READ_ENABLED": True, "KRAKEN_API_KEY": "key", "KRAKEN_API_SECRET": secret()}
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_kraken_private_client_reports_unconfigured_when_keys_missing() -> None:
    """Missing keys report unconfigured."""
    client = KrakenPrivateClient(settings=Settings(_env_file=None))
    assert client.is_configured() is False


def test_private_calls_refused_when_read_disabled() -> None:
    """Disabled private read refuses calls."""
    client = KrakenPrivateClient(settings=settings(KRAKEN_PRIVATE_READ_ENABLED=False), request_fn=lambda endpoint, data: {"error": [], "result": {}})
    with pytest.raises(KrakenPrivateDisabledError):
        client.get_account_balance()


def test_get_account_balance_parses_mocked_balance_response() -> None:
    """Balance response parses."""
    client = KrakenPrivateClient(settings=settings(), request_fn=lambda endpoint, data: {"error": [], "result": {"XXBT": "1.25", "ZUSD": "100.5"}})
    balances = client.get_account_balance()
    assert balances[0].asset == "XXBT"
    assert balances[0].balance == 1.25


def test_get_extended_balance_parses_mocked_balance_ex_response() -> None:
    """BalanceEx response parses."""
    response = {
        "error": [],
        "result": {
            "XXBT": {"balance": "1.25", "available": "1.0", "hold_trade": "0.25", "credit": "0", "credit_used": "0"}
        },
    }
    client = KrakenPrivateClient(settings=settings(), request_fn=lambda endpoint, data: response)
    balances = client.get_extended_balance()
    assert balances[0].available == 1.0
    assert balances[0].hold == 0.25
