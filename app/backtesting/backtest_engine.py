"""Crypto Hunter backtesting engine."""

from __future__ import annotations

from uuid import uuid4

import pandas as pd

from app.backtesting.backtest_data import dataframe_from_kraken_candles
from app.backtesting.backtest_models import BacktestConfig, BacktestEquityPoint, BacktestResult, BacktestTrade
from app.backtesting.performance_metrics import (
    calculate_average_win_loss,
    calculate_fees_total,
    calculate_max_drawdown,
    calculate_profit_factor,
    calculate_total_return,
    calculate_win_rate,
)
from app.config import get_settings
from app.strategies.indicator_engine import IndicatorEngine
from app.strategies.signal_scoring import SignalScoringEngine


class BacktestDataError(ValueError):
    """Raised when backtest data is invalid."""


class BacktestEngine:
    """Run Crypto Hunter's long-only strategy over historical candles."""

    REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}

    def __init__(self, indicator_engine: IndicatorEngine | None = None, scoring_engine: SignalScoringEngine | None = None) -> None:
        """Initialize the backtest engine."""
        self.indicator_engine = indicator_engine or IndicatorEngine()
        self.scoring_engine = scoring_engine or SignalScoringEngine()

    def run_single_symbol_backtest(self, df: pd.DataFrame, symbol: str, timeframe: str = "1h", config: BacktestConfig | None = None) -> BacktestResult:
        """Run a single-symbol backtest."""
        self.validate_backtest_data(df)
        cfg = config or self._default_config(timeframe)
        candles = dataframe_from_kraken_candles(df).copy(deep=True).sort_values("timestamp").reset_index(drop=True)
        candles["symbol"] = symbol
        candles["exchange_symbol"] = symbol.replace("/", "")
        enriched = self.indicator_engine.add_indicators(candles)
        cash = cfg.starting_cash
        realized_pnl = 0.0
        position = None
        trades: list[BacktestTrade] = []
        equity_curve: list[BacktestEquityPoint] = []
        peak_equity = cfg.starting_cash
        warnings: list[str] = []

        for idx in range(200, len(enriched)):
            row = enriched.iloc[idx]
            price = float(row["close"])
            if position is not None:
                previous_row = enriched.iloc[idx - 1] if idx > 0 else row
                exit_reason = self._exit_reason(position, row, previous_row, idx == len(enriched) - 1)
                if exit_reason:
                    exit_price = self._sell_fill(price, cfg)
                    quantity = position["quantity"]
                    notional = quantity * exit_price
                    exit_fee = notional * cfg.fee_rate
                    gross = (exit_price - position["entry_price"]) * quantity
                    net = gross - position["entry_fee"] - exit_fee
                    cash += notional - exit_fee
                    realized_pnl += net
                    trades.append(
                        BacktestTrade(
                            trade_id=str(uuid4()),
                            symbol=symbol,
                            side="long",
                            entry_time=position["entry_time"],
                            exit_time=row["timestamp"],
                            entry_price=position["entry_price"],
                            exit_price=exit_price,
                            quantity=quantity,
                            entry_fee=position["entry_fee"],
                            exit_fee=exit_fee,
                            gross_pnl=gross,
                            net_pnl=net,
                            return_pct=(net / (position["entry_price"] * quantity)) * 100,
                            exit_reason=exit_reason,
                            signal_score=position["signal_score"],
                        )
                    )
                    position = None

            if position is None and idx < len(enriched) - 1:
                signal_df = enriched.iloc[: idx + 1]
                signal = self.scoring_engine.score(signal_df, timeframe=timeframe, symbol=symbol)
                next_open = float(enriched.iloc[idx + 1]["open"])
                if self._can_enter(signal, row, cfg):
                    fill = self._buy_fill(next_open, cfg)
                    risk_cash = cash * 0.25
                    quantity = risk_cash / fill if fill > 0 else 0.0
                    entry_fee = quantity * fill * cfg.fee_rate
                    if quantity > 0 and cash >= quantity * fill + entry_fee:
                        cash -= quantity * fill + entry_fee
                        position = {
                            "quantity": quantity,
                            "entry_price": fill,
                            "entry_fee": entry_fee,
                            "entry_time": enriched.iloc[idx + 1]["timestamp"],
                            "stop": signal.suggested_stop_loss,
                            "take_profit": signal.suggested_take_profit,
                            "signal_score": signal.score,
                            "was_profitable": False,
                        }

            open_value = 0.0 if position is None else position["quantity"] * price
            unrealized = 0.0 if position is None else ((price - position["entry_price"]) * position["quantity"]) - position["entry_fee"]
            if position is not None and unrealized > 0:
                position["was_profitable"] = True
            equity = cash + open_value
            peak_equity = max(peak_equity, equity)
            drawdown = ((peak_equity - equity) / peak_equity) * 100 if peak_equity > 0 else 0.0
            equity_curve.append(BacktestEquityPoint(row["timestamp"], cash, equity, open_value, realized_pnl, unrealized, drawdown))

        ending_equity = equity_curve[-1].equity if equity_curve else cfg.starting_cash
        average_win, average_loss = calculate_average_win_loss(trades)
        return BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            starting_cash=cfg.starting_cash,
            ending_cash=cash,
            ending_equity=ending_equity,
            total_return_pct=calculate_total_return(cfg.starting_cash, ending_equity),
            max_drawdown_pct=calculate_max_drawdown(equity_curve),
            total_trades=len(trades),
            winning_trades=sum(1 for trade in trades if trade.net_pnl > 0),
            losing_trades=sum(1 for trade in trades if trade.net_pnl < 0),
            win_rate=calculate_win_rate(trades),
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=calculate_profit_factor(trades),
            total_fees=calculate_fees_total(trades),
            trades=trades,
            equity_curve=equity_curve,
            warnings=warnings,
        )

    def run_watchlist_backtest(self, symbol_to_df: dict, timeframe: str = "1h", config: BacktestConfig | None = None) -> dict:
        """Run backtests for multiple symbols."""
        return {symbol: self.run_single_symbol_backtest(df, symbol, timeframe, config) for symbol, df in symbol_to_df.items()}

    def validate_backtest_data(self, df: pd.DataFrame) -> None:
        """Validate OHLCV backtest data."""
        if df is None or df.empty:
            raise BacktestDataError("Backtest DataFrame is empty")
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise BacktestDataError(f"Missing backtest columns: {sorted(missing)}")
        if len(df) < 220:
            raise BacktestDataError("At least 220 candles are required for backtesting")

    def _default_config(self, timeframe: str) -> BacktestConfig:
        """Build config from app settings."""
        settings = get_settings()
        return BacktestConfig(
            starting_cash=settings.backtest_starting_cash,
            fee_rate=settings.backtest_fee_rate,
            slippage_bps=settings.backtest_slippage_bps,
            timeframe=timeframe,
            min_signal_score=settings.backtest_min_signal_score,
            allow_shorts=settings.backtest_allow_shorts,
            max_open_positions=settings.backtest_max_open_positions,
        )

    def _can_enter(self, signal, row, config: BacktestConfig) -> bool:
        """Return whether a long entry is allowed."""
        return (
            signal.score >= config.min_signal_score
            and signal.category == "STRONG_BUY"
            and not signal.blockers
            and float(row["close"]) > float(row["ema_200"])
        )

    def _exit_reason(self, position: dict, row, previous_row, final: bool) -> str | None:
        """Return exit reason if exit conditions are met."""
        close = float(row["close"])
        low = float(row["low"])
        high = float(row["high"])
        if position.get("stop") is not None and low <= float(position["stop"]):
            return "stop_loss"
        if position.get("take_profit") is not None and high >= float(position["take_profit"]):
            return "take_profit"
        if float(row["macd_line"]) < float(row["macd_signal"]):
            return "macd_bearish"
        if position.get("was_profitable") and close < float(row["ema_20"]):
            return "lost_ema_20_after_profit"
        previous_rsi = float(previous_row["rsi_14"])
        if previous_rsi > 70 and float(row["rsi_14"]) < 70:
            return "rsi_cross_down_from_overbought"
        if final:
            return "final_candle"
        return None

    def _buy_fill(self, price: float, config: BacktestConfig) -> float:
        """Apply buy slippage."""
        return price * (1 + config.slippage_bps / 10000)

    def _sell_fill(self, price: float, config: BacktestConfig) -> float:
        """Apply sell slippage."""
        return price * (1 - config.slippage_bps / 10000)
