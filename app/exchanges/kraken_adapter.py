"""Kraken exchange adapter skeleton for Phase 1."""

from typing import Any

from app.config import Settings, get_settings
from app.exchanges.base import BaseExchange


class KrakenAdapter(BaseExchange):
    """Kraken adapter with read-oriented placeholders and no live order placement."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the Kraken adapter."""
        self.settings = settings or get_settings()

    def get_symbols(self) -> list[str]:
        """Return configured Kraken symbols."""
        return self.settings.allowed_symbols

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> Any:
        """Return candle data placeholder for Phase 1."""
        return []

    def get_ticker(self, symbol: str) -> dict:
        """Return ticker placeholder for Phase 1."""
        return {"symbol": self.normalize_symbol(symbol), "price": None}

    def get_orderbook(self, symbol: str) -> dict:
        """Return orderbook placeholder for Phase 1."""
        return {"symbol": self.normalize_symbol(symbol), "bids": [], "asks": []}

    def get_balance(self) -> dict:
        """Return empty balance data without exposing credentials."""
        return {}

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Refuse live orders because Kraken execution is not implemented in Phase 1."""
        raise NotImplementedError("Kraken live order placement is not implemented in Phase 1")

    def cancel_order(self, order_id: str) -> dict:
        """Refuse cancellation because live order management is not implemented in Phase 1."""
        raise NotImplementedError("Kraken live order cancellation is not implemented in Phase 1")

    def get_open_orders(self) -> list[dict]:
        """Return no open live orders in Phase 1."""
        return []

    def get_positions(self) -> list[dict]:
        """Return no live positions in Phase 1."""
        return []

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbols to Kraken-style slash pairs."""
        cleaned = symbol.strip().upper().replace("-", "/")
        if "/" not in cleaned and cleaned.endswith(self.settings.base_currency):
            base = cleaned[: -len(self.settings.base_currency)]
            cleaned = f"{base}/{self.settings.base_currency}"
        return cleaned
