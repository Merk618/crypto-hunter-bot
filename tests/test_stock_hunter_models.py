"""Stock Hunter model tests."""

from app.config import Settings
from app.stock_hunter.stock_hunter_models import StockSignalResult, StockWatchlistItem


def test_stock_hunter_config_defaults_disabled_read_only() -> None:
    """Stock Hunter defaults are safe."""
    settings = Settings(_env_file=None)

    assert settings.stock_hunter_enabled is False
    assert settings.stock_hunter_allow_trading is False
    assert settings.stock_hunter_read_only is True


def test_stock_models_serialize() -> None:
    """Basic models return dictionaries."""
    item = StockWatchlistItem(symbol="AAPL")
    signal = StockSignalResult("AAPL", 80, "LEADING", [], [], [], 100.0, "BULLISH", "ABOVE_AVERAGE")

    assert item.to_dict()["symbol"] == "AAPL"
    assert signal.to_dict()["source"] == "stock_hunter_signal_v1"
