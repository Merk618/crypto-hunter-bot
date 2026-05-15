"""Trade executor paper routing tests."""

import pytest

from app.config import Settings
from app.execution.paper_broker import PaperBroker
from app.execution.trade_executor import TradeExecutor
from app.main import app
from app.portfolio.paper_account import PaperAccount


def test_trade_executor_routes_to_paper_broker_in_paper_mode() -> None:
    """TradeExecutor routes paper mode to PaperBroker."""
    settings = Settings(_env_file=None, BOT_MODE="paper")
    paper_broker = PaperBroker(account=PaperAccount(), settings=settings)
    executor = TradeExecutor(paper_broker=paper_broker, settings=settings)
    result = executor.execute_paper_market_order("BTC/USD", "buy", 0.1, 10000)
    assert result["accepted"] is True
    assert executor.get_paper_account_summary()["open_positions"] == 1


def test_trade_executor_refuses_live_mode_order_execution() -> None:
    """TradeExecutor refuses live mode execution."""
    settings = Settings(_env_file=None, BOT_MODE="live")
    executor = TradeExecutor(paper_broker=PaperBroker(settings=settings), settings=settings)
    with pytest.raises(RuntimeError):
        executor.execute_paper_market_order("BTC/USD", "buy", 0.1, 10000)


def test_fastapi_paper_routes_exist() -> None:
    """Paper trading routes are registered."""
    paths = {route.path for route in app.routes}
    assert "/paper/account" in paths
    assert "/paper/positions" in paths
    assert "/paper/orders" in paths
    assert "/paper/fills" in paths
    assert "/paper/order" in paths
    assert "/paper/close/{symbol}" in paths
    assert "/paper/reset" in paths


def test_no_live_trading_routes_were_added() -> None:
    """No live trading routes exist."""
    paths = {route.path for route in app.routes}
    assert not any(path.startswith("/live") for path in paths)


def test_no_withdrawal_methods_exist() -> None:
    """No withdrawal functionality is exposed by route names."""
    paths = {route.path.lower() for route in app.routes}
    assert not any("withdraw" in path for path in paths)
