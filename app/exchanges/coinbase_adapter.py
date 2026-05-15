"""Coinbase exchange adapter placeholder for a later phase."""

from typing import Any

from app.config import Settings, get_settings
from app.exchanges.base import BaseExchange


class CoinbaseAdapter(BaseExchange):
    """Coinbase adapter placeholder with no live execution."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the Coinbase adapter placeholder."""
        self.settings = settings or get_settings()

    def get_symbols(self) -> list[str]:
        """Return configured symbols normalized for Coinbase style."""
        return [self.normalize_symbol(symbol) for symbol in self.settings.allowed_symbols]

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> Any:
        """Return candle placeholder data."""
        return []

    def get_ticker(self, symbol: str) -> dict:
        """Return ticker placeholder data."""
        return {"symbol": self.normalize_symbol(symbol), "price": None}

    def get_orderbook(self, symbol: str) -> dict:
        """Return orderbook placeholder data."""
        return {"symbol": self.normalize_symbol(symbol), "bids": [], "asks": []}

    def get_balance(self) -> dict:
        """Return empty balance data."""
        return {}

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Refuse orders because Coinbase execution is a placeholder in Phase 1."""
        raise NotImplementedError("Coinbase live order placement is not implemented in Phase 1")

    def cancel_order(self, order_id: str) -> dict:
        """Refuse cancellation because Coinbase execution is a placeholder in Phase 1."""
        raise NotImplementedError("Coinbase order cancellation is not implemented in Phase 1")

    def get_open_orders(self) -> list[dict]:
        """Return no open orders."""
        return []

    def get_positions(self) -> list[dict]:
        """Return no positions."""
        return []

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbols to Coinbase hyphen pairs."""
        return symbol.strip().upper().replace("/", "-")
