"""In-memory stock watchlist for Stock/Options Hunter."""

from __future__ import annotations

import re

from app.config import Settings, get_settings
from app.stock_hunter.stock_hunter_models import StockWatchlistItem


class StockWatchlistError(ValueError):
    """Raised for invalid watchlist symbols."""


class StockWatchlist:
    """Manage a simple in-memory stock watchlist."""

    SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize watchlist from default symbols."""
        self.settings = settings or get_settings()
        self._items: dict[str, StockWatchlistItem] = {}
        for priority, symbol in enumerate(self.settings.stock_hunter_default_symbols, start=1):
            self.add_symbol(symbol, priority=priority)

    def add_symbol(self, symbol: str, name: str | None = None, sector: str | None = None, priority: int = 100, notes: str | None = None) -> StockWatchlistItem:
        """Add or update a symbol."""
        normalized = self.normalize_symbol(symbol)
        item = StockWatchlistItem(symbol=normalized, name=name, sector=sector, priority=priority, enabled=True, notes=notes)
        self._items[normalized] = item
        return item

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol if present."""
        self._items.pop(self.normalize_symbol(symbol), None)

    def enable_symbol(self, symbol: str) -> None:
        """Enable a symbol."""
        self._items[self.normalize_symbol(symbol)].enabled = True

    def disable_symbol(self, symbol: str) -> None:
        """Disable a symbol."""
        self._items[self.normalize_symbol(symbol)].enabled = False

    def get_items(self) -> list[StockWatchlistItem]:
        """Return all watchlist items sorted by priority."""
        return sorted(self._items.values(), key=lambda item: (item.priority, item.symbol))

    def get_active_symbols(self) -> list[str]:
        """Return enabled symbols."""
        return [item.symbol for item in self.get_items() if item.enabled]

    def to_dict(self) -> dict:
        """Return watchlist as JSON-friendly data."""
        return {"items": [item.to_dict() for item in self.get_items()], "active_symbols": self.get_active_symbols()}

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize and validate a stock symbol."""
        normalized = symbol.strip().upper()
        if not self.SYMBOL_RE.match(normalized):
            raise StockWatchlistError(f"Invalid stock symbol: {symbol}")
        return normalized
