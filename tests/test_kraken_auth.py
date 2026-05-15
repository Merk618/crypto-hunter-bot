"""Kraken auth tests."""

import base64

from app.exchanges.kraken_auth import KrakenAuth


def test_kraken_auth_generates_signature_without_exposing_secrets() -> None:
    """KrakenAuth signs requests and repr redacts credentials."""
    secret = base64.b64encode(b"test-secret").decode("utf-8")
    auth = KrakenAuth("public-key", secret, nonce_fn=lambda: "123")
    data = {"nonce": "123"}
    signature = auth.sign("/0/private/Balance", data)
    assert isinstance(signature, str)
    assert signature
    safe_repr = repr(auth)
    assert "public-key" not in safe_repr
    assert secret not in safe_repr
    assert "redacted" in safe_repr
