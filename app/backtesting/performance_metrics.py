"""Backtest performance metrics."""

from app.backtesting.backtest_models import BacktestTrade


def calculate_total_return(starting_equity: float, ending_equity: float) -> float:
    """Calculate percentage total return."""
    if starting_equity <= 0:
        return 0.0
    return ((ending_equity - starting_equity) / starting_equity) * 100


def calculate_max_drawdown(equity_curve) -> float:
    """Calculate max drawdown percent from equity curve."""
    peak = None
    max_dd = 0.0
    for point in equity_curve:
        equity = point.equity if hasattr(point, "equity") else float(point["equity"])
        peak = equity if peak is None else max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, ((peak - equity) / peak) * 100)
    return max_dd


def calculate_win_rate(trades: list[BacktestTrade]) -> float:
    """Calculate win rate percentage."""
    if not trades:
        return 0.0
    return (sum(1 for trade in trades if trade.net_pnl > 0) / len(trades)) * 100


def calculate_profit_factor(trades: list[BacktestTrade]) -> float:
    """Calculate gross profit divided by gross loss."""
    wins = sum(trade.net_pnl for trade in trades if trade.net_pnl > 0)
    losses = abs(sum(trade.net_pnl for trade in trades if trade.net_pnl < 0))
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return wins / losses


def calculate_average_win_loss(trades: list[BacktestTrade]) -> tuple[float, float]:
    """Calculate average winning and losing trade."""
    wins = [trade.net_pnl for trade in trades if trade.net_pnl > 0]
    losses = [trade.net_pnl for trade in trades if trade.net_pnl < 0]
    return (sum(wins) / len(wins) if wins else 0.0, sum(losses) / len(losses) if losses else 0.0)


def calculate_fees_total(trades: list[BacktestTrade]) -> float:
    """Calculate total fees."""
    return sum(trade.entry_fee + trade.exit_fee for trade in trades)
