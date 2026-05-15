"""Backtest engine tests with synthetic data."""

import numpy as np
import pandas as pd
import pytest

from app.backtesting.backtest_engine import BacktestDataError, BacktestEngine
from app.backtesting.backtest_models import BacktestConfig, BacktestResult


class FakeSignal:
    """Fake scoring signal."""

    def __init__(self, score=90, category="STRONG_BUY", blockers=None, stop=95.0, take=120.0):
        """Initialize fake signal."""
        self.score = score
        self.category = category
        self.blockers = blockers or []
        self.suggested_stop_loss = stop
        self.suggested_take_profit = take


class FakeScorer:
    """Fake scorer returning deterministic signals."""

    def __init__(self, signal: FakeSignal):
        """Initialize fake scorer."""
        self.signal = signal
        self.calls = 0

    def score(self, df, timeframe="1h", symbol=None):
        """Return fake signal."""
        self.calls += 1
        return self.signal


def candles(rows=260, trend="up") -> pd.DataFrame:
    """Build synthetic candles."""
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    if trend == "down":
        close = np.linspace(160, 100, rows)
    else:
        close = np.linspace(100, 160, rows)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close,
            "high": close + 2,
            "low": close - 2,
            "close": close + 1,
            "volume": 1000.0,
        }
    )


def engine(signal=None) -> BacktestEngine:
    """Build engine with fake scorer."""
    return BacktestEngine(scoring_engine=FakeScorer(signal or FakeSignal()))  # type: ignore[arg-type]


def test_backtest_rejects_empty_dataframe() -> None:
    """Empty data rejects."""
    with pytest.raises(BacktestDataError):
        BacktestEngine().validate_backtest_data(pd.DataFrame())


def test_backtest_rejects_missing_ohlcv_columns() -> None:
    """Missing columns reject."""
    with pytest.raises(BacktestDataError):
        BacktestEngine().validate_backtest_data(candles().drop(columns=["close"]))


def test_backtest_does_not_mutate_input_dataframe() -> None:
    """Engine does not mutate input."""
    df = candles()
    cols = list(df.columns)
    engine().run_single_symbol_backtest(df, "BTC/USD")
    assert list(df.columns) == cols


def test_backtest_runs_on_bullish_synthetic_data() -> None:
    """Bullish data runs."""
    result = engine().run_single_symbol_backtest(candles(), "BTC/USD")
    assert isinstance(result, BacktestResult)
    assert result.equity_curve


def test_backtest_runs_on_bearish_synthetic_data() -> None:
    """Bearish data runs."""
    result = engine(FakeSignal(score=10, category="AVOID_SELL")).run_single_symbol_backtest(candles(trend="down"), "BTC/USD")
    assert isinstance(result, BacktestResult)


def test_entry_happens_only_after_valid_signal() -> None:
    """Low score produces no trades."""
    result = engine(FakeSignal(score=50, category="NEUTRAL")).run_single_symbol_backtest(candles(), "BTC/USD")
    assert result.total_trades == 0


def test_no_lookahead_bias_execution_uses_next_candle_price() -> None:
    """Entry uses next candle open with slippage."""
    df = candles()
    result = engine().run_single_symbol_backtest(df, "BTC/USD")
    if result.trades:
        # First possible signal index is 200; execution at 201 open with buy slippage.
        assert result.trades[0].entry_price == pytest.approx(float(df.iloc[201]["open"]) * 1.001)


def test_stop_loss_exit_works() -> None:
    """Stop loss exits."""
    df = candles()
    df.loc[205:, "low"] = 50
    result = engine(FakeSignal(stop=90, take=1000)).run_single_symbol_backtest(df, "BTC/USD")
    assert any(trade.exit_reason == "stop_loss" for trade in result.trades)


def test_take_profit_exit_works() -> None:
    """Take profit exits."""
    df = candles()
    df.loc[205:, "high"] = 500
    result = engine(FakeSignal(stop=1, take=120)).run_single_symbol_backtest(df, "BTC/USD")
    assert any(trade.exit_reason == "take_profit" for trade in result.trades)


def test_final_candle_closes_open_position() -> None:
    """Final candle closes open position."""
    result = engine(FakeSignal(stop=1, take=10000)).run_single_symbol_backtest(candles(), "BTC/USD")
    assert result.trades
    assert result.trades[-1].exit_reason == "final_candle"


def test_fees_and_slippage_are_applied() -> None:
    """Fees and slippage appear on trades."""
    result = engine().run_single_symbol_backtest(candles(), "BTC/USD")
    assert result.total_fees >= 0
    if result.trades:
        assert result.trades[0].entry_fee > 0
        assert result.trades[0].entry_price > 0


def test_equity_curve_and_metrics_are_generated() -> None:
    """Equity curve and metrics exist."""
    result = engine().run_single_symbol_backtest(candles(), "BTC/USD")
    assert result.equity_curve
    assert result.max_drawdown_pct >= 0
    assert result.win_rate >= 0
    assert result.profit_factor >= 0


def test_no_short_trades_are_created() -> None:
    """No shorts are created."""
    result = engine().run_single_symbol_backtest(candles(), "BTC/USD", config=BacktestConfig(allow_shorts=False))
    assert all(trade.side == "long" for trade in result.trades)


def test_watchlist_backtest_handles_multiple_symbols() -> None:
    """Watchlist backtest handles multiple symbols."""
    results = engine().run_watchlist_backtest({"BTC/USD": candles(), "ETH/USD": candles()}, "1h")
    assert set(results) == {"BTC/USD", "ETH/USD"}


def test_fastapi_backtest_routes_exist() -> None:
    """Backtest routes are registered."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/backtest/single" in paths
    assert "/backtest/watchlist" in paths


def test_no_live_trading_or_withdrawal_routes_exist() -> None:
    """No live trading or withdrawal routes exist."""
    from app.main import app

    paths = {route.path.lower() for route in app.routes}
    assert not any(path.startswith("/live") for path in paths)
    assert not any("withdraw" in path for path in paths)
