"""Kraken private REST signing helper."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode


class KrakenAuth:
    """Build signed Kraken private REST headers without exposing secrets."""

    def __init__(self, api_key: str, api_secret: str, nonce_fn=None) -> None:
        """Initialize Kraken auth credentials."""
        self._api_key = api_key
        self._api_secret = api_secret
        self._nonce_fn = nonce_fn or (lambda: str(int(time.time() * 1000)))

    def nonce(self) -> str:
        """Return a monotonically increasing nonce string."""
        return str(self._nonce_fn())

    def sign(self, url_path: str, data: dict) -> str:
        """Create Kraken API-Sign header value."""
        postdata = urlencode(data)
        encoded = (str(data["nonce"]) + postdata).encode("utf-8")
        message = url_path.encode("utf-8") + hashlib.sha256(encoded).digest()
        secret = base64.b64decode(self._api_secret)
        signature = hmac.new(secret, message, hashlib.sha512)
        return base64.b64encode(signature.digest()).decode("utf-8")

    def headers(self, url_path: str, data: dict) -> dict:
        """Return signed Kraken private REST headers."""
        return {"API-Key": self._api_key, "API-Sign": self.sign(url_path, data)}

    def __repr__(self) -> str:
        """Return safe representation without secrets."""
        return "KrakenAuth(api_key=<redacted>, api_secret=<redacted>)"
