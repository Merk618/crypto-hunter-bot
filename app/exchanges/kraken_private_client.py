"""Kraken private read-only REST client."""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import Settings, get_settings
from app.exchanges.kraken_account_models import ExchangeBalance, ExchangeAccountSummary
from app.exchanges.kraken_auth import KrakenAuth


class KrakenPrivateClientError(RuntimeError):
    """Base error for Kraken private read client."""


class KrakenPrivateDisabledError(KrakenPrivateClientError):
    """Raised when private reads are disabled."""


class KrakenPrivateNotConfiguredError(KrakenPrivateClientError):
    """Raised when private credentials are missing."""


class KrakenPrivateRequestError(KrakenPrivateClientError):
    """Raised when a Kraken private request fails."""


class KrakenPrivateClient:
    """Read-only Kraken private account client."""

    BASE_URL = "https://api.kraken.com"

    def __init__(self, settings: Settings | None = None, request_fn=None, auth: KrakenAuth | None = None) -> None:
        """Initialize client."""
        self.settings = settings or get_settings()
        self._request_fn = request_fn
        self.auth = auth or KrakenAuth(self.settings.kraken_api_key, self.settings.kraken_api_secret) if self.is_configured() else None

    def is_configured(self) -> bool:
        """Return True when API key and secret are present."""
        return bool(self.settings.kraken_api_key and self.settings.kraken_api_secret)

    def get_account_balance(self) -> list[ExchangeBalance]:
        """Read Kraken private Balance endpoint."""
        result = self._private_request("Balance")
        return [ExchangeBalance(asset=asset, balance=float(balance), available=float(balance), raw={"balance": balance}) for asset, balance in result.items()]

    def get_extended_balance(self) -> list[ExchangeBalance]:
        """Read Kraken private BalanceEx endpoint."""
        result = self._private_request("BalanceEx")
        balances = []
        for asset, data in result.items():
            balances.append(
                ExchangeBalance(
                    asset=asset,
                    balance=float(data.get("balance", 0) or 0),
                    available=float(data.get("available", 0) or 0),
                    hold=float(data.get("hold_trade", data.get("hold", 0)) or 0),
                    credit=float(data.get("credit", 0) or 0),
                    credit_used=float(data.get("credit_used", 0) or 0),
                    raw=data,
                )
            )
        return balances

    def get_trade_balance(self) -> dict:
        """Read Kraken private TradeBalance endpoint."""
        return self._private_request("TradeBalance")

    def get_open_orders_read_only(self) -> dict:
        """Read open orders without creating, editing, or cancelling orders."""
        return self._private_request("OpenOrders")

    def get_account_summary(self) -> ExchangeAccountSummary:
        """Return read-only account summary using extended balances when available."""
        balances = self.get_extended_balance()
        return ExchangeAccountSummary(
            exchange="kraken",
            private_read_enabled=self.settings.kraken_private_read_enabled,
            configured=self.is_configured(),
            balances=balances,
            total_assets_count=len(balances),
            nonzero_assets_count=sum(1 for balance in balances if balance.balance != 0),
            warnings=[],
        )

    def _assert_read_allowed(self) -> None:
        """Raise unless private read is enabled and configured."""
        if not self.settings.kraken_private_read_enabled:
            raise KrakenPrivateDisabledError("Kraken private account read is disabled")
        if not self.is_configured():
            raise KrakenPrivateNotConfiguredError("Kraken private API credentials are missing")

    def _private_request(self, endpoint: str, data: dict | None = None) -> dict:
        """Call a Kraken private endpoint and return result."""
        self._assert_read_allowed()
        payload = dict(data or {})
        assert self.auth is not None
        payload["nonce"] = self.auth.nonce()
        if self._request_fn:
            response = self._request_fn(endpoint, payload)
        else:
            response = self._urlopen_private(endpoint, payload)
        errors = response.get("error") or []
        if errors:
            raise KrakenPrivateRequestError(f"Kraken private request failed for {endpoint}: {', '.join(errors)}")
        return response.get("result", {})

    def _urlopen_private(self, endpoint: str, payload: dict) -> dict:
        """Perform a signed urllib request."""
        url_path = f"/0/private/{endpoint}"
        body = urlencode(payload).encode("utf-8")
        request = Request(f"{self.BASE_URL}{url_path}", data=body, headers=self.auth.headers(url_path, payload))
        try:
            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise KrakenPrivateRequestError(f"Kraken private request failed for {endpoint}") from exc
