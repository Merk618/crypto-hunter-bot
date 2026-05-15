"""Performance metric tests."""

from app.backtesting.backtest_models import BacktestEquityPoint, BacktestTrade
from app.backtesting.performance_metrics import (
    calculate_average_win_loss,
    calculate_fees_total,
    calculate_max_drawdown,
    calculate_profit_factor,
    calculate_total_return,
    calculate_win_rate,
)


def trade(net: float) -> BacktestTrade:
    """Build a trade with net PnL."""
    return BacktestTrade("t", "BTC/USD", "long", "a", "b", 100, 110, 1, 1, 1, net + 2, net, net, "x", 90)


def test_performance_metrics() -> None:
    """Metrics calculate expected values."""
    trades = [trade(10), trade(-5)]
    curve = [BacktestEquityPoint("a", 0, 100, 0, 0, 0, 0), BacktestEquityPoint("b", 0, 80, 0, 0, 0, 20)]
    assert calculate_total_return(100, 110) == 10
    assert calculate_max_drawdown(curve) == 20
    assert calculate_win_rate(trades) == 50
    assert calculate_profit_factor(trades) == 2
    assert calculate_average_win_loss(trades) == (10, -5)
    assert calculate_fees_total(trades) == 4
