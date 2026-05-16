"""Stock watchlist tests."""

import pytest

from app.config import Settings
from app.stock_hunter.stock_watchlist import StockWatchlist, StockWatchlistError


def test_watchlist_loads_default_symbols() -> None:
    """Default symbols come from config."""
    watchlist = StockWatchlist(Settings(_env_file=None))

    assert watchlist.get_active_symbols()[:3] == ["AAPL", "MSFT", "NVDA"]


def test_watchlist_normalizes_symbols() -> None:
    """Symbols are normalized uppercase."""
    watchlist = StockWatchlist(Settings(_env_file=None, STOCK_HUNTER_DEFAULT_SYMBOLS="AAPL"))
    item = watchlist.add_symbol("msft")

    assert item.symbol == "MSFT"
    assert "MSFT" in watchlist.get_active_symbols()


def test_watchlist_rejects_invalid_symbols() -> None:
    """Invalid symbols are rejected."""
    watchlist = StockWatchlist(Settings(_env_file=None, STOCK_HUNTER_DEFAULT_SYMBOLS="AAPL"))

    with pytest.raises(StockWatchlistError):
        watchlist.add_symbol("BAD SYMBOL!")
