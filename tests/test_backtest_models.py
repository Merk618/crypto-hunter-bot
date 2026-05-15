"""Backtest model tests."""

from app.backtesting.backtest_models import BacktestConfig, BacktestTrade


def test_backtest_config_defaults() -> None:
    """BacktestConfig exposes safe defaults."""
    config = BacktestConfig()
    assert config.starting_cash == 10000
    assert config.allow_shorts is False


def test_backtest_trade_to_dict() -> None:
    """BacktestTrade serializes to dict."""
    trade = BacktestTrade("id", "BTC/USD", "long", "a", "b", 100, 110, 1, 1, 1, 10, 8, 8, "take_profit", 90)
    assert trade.to_dict()["trade_id"] == "id"
