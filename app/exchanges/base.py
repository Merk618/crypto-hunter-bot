"""Exchange adapter interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseExchange(ABC):
    """Abstract interface every exchange adapter must implement."""

    @abstractmethod
    def get_symbols(self) -> list[str]:
        """Return tradable symbols."""

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, limit: int) -> Any:
        """Return OHLCV candles for a symbol."""

    @abstractmethod
    def get_ticker(self, symbol: str) -> dict:
        """Return the latest ticker data."""

    @abstractmethod
    def get_orderbook(self, symbol: str) -> dict:
        """Return orderbook data."""

    @abstractmethod
    def get_balance(self) -> dict:
        """Return account balance data."""

    @abstractmethod
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Place an order or refuse if unavailable."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict:
        """Cancel an open order."""

    @abstractmethod
    def get_open_orders(self) -> list[dict]:
        """Return currently open orders."""

    @abstractmethod
    def get_positions(self) -> list[dict]:
        """Return open positions."""

    @abstractmethod
    def normalize_symbol(self, symbol: str) -> str:
        """Normalize a symbol to the exchange's expected format."""
