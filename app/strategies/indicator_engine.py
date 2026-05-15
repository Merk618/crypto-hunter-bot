"""Technical indicator engine for candle DataFrames."""

from __future__ import annotations

import numpy as np
import pandas as pd


class IndicatorEngineError(ValueError):
    """Base exception for indicator engine validation failures."""


class MissingCandleColumnsError(IndicatorEngineError):
    """Raised when required candle columns are missing."""


class NotEnoughCandleDataError(IndicatorEngineError):
    """Raised when there are not enough candles for long indicators."""


class InvalidNumericCandleValuesError(IndicatorEngineError):
    """Raised when required OHLCV columns contain invalid numeric data."""


class EmptyCandleDataFrameError(IndicatorEngineError):
    """Raised when candle data is empty."""


class IndicatorEngine:
    """Compute Crypto Hunter indicators from Phase 2 candle DataFrames."""

    REQUIRED_COLUMNS = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "vwap",
        "volume",
        "count",
        "symbol",
        "exchange_symbol",
    }
    REQUIRED_NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume"]
    MIN_CANDLES = 200
    INDICATOR_COLUMNS = [
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "macd_line",
        "macd_signal",
        "macd_histogram",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "bb_percent_b",
        "atr_14",
        "obv",
        "obv_slope_5",
        "obv_trend_positive",
        "adx",
        "plus_di",
        "minus_di",
        "volume_sma_20",
        "volume_above_sma_20",
    ]

    def validate_candle_dataframe(self, df: pd.DataFrame) -> None:
        """Validate candle input before indicator calculation."""
        if df is None or df.empty:
            raise EmptyCandleDataFrameError("Candle DataFrame is empty")

        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise MissingCandleColumnsError(f"Missing required candle columns: {sorted(missing)}")

        if len(df) < self.MIN_CANDLES:
            raise NotEnoughCandleDataError(f"At least {self.MIN_CANDLES} candles are required")

        for column in self.REQUIRED_NUMERIC_COLUMNS:
            numeric = pd.to_numeric(df[column], errors="coerce")
            if numeric.isna().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
                raise InvalidNumericCandleValuesError(f"Column contains invalid numeric values: {column}")

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a new DataFrame with all Phase 3 indicator columns added."""
        self.validate_candle_dataframe(df)
        out = df.copy(deep=True).sort_values("timestamp", ascending=True).reset_index(drop=True)

        for column in self.REQUIRED_NUMERIC_COLUMNS + ["vwap"]:
            out[column] = pd.to_numeric(out[column], errors="coerce").astype(float)

        close = out["close"]
        high = out["high"]
        low = out["low"]
        volume = out["volume"]

        out["ema_20"] = self._ema(close, 20)
        out["ema_50"] = self._ema(close, 50)
        out["ema_200"] = self._ema(close, 200)
        out["rsi_14"] = self._rsi(close, 14)

        ema_12 = self._ema(close, 12)
        ema_26 = self._ema(close, 26)
        out["macd_line"] = ema_12 - ema_26
        out["macd_signal"] = self._ema(out["macd_line"], 9)
        out["macd_histogram"] = out["macd_line"] - out["macd_signal"]

        out["bb_middle"] = close.rolling(window=20, min_periods=20).mean()
        bb_std = close.rolling(window=20, min_periods=20).std(ddof=0)
        out["bb_upper"] = out["bb_middle"] + (bb_std * 2)
        out["bb_lower"] = out["bb_middle"] - (bb_std * 2)
        out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_middle"]
        band_range = out["bb_upper"] - out["bb_lower"]
        out["bb_percent_b"] = (close - out["bb_lower"]) / band_range.replace(0, np.nan)

        out["atr_14"] = self._atr(high, low, close, 14)
        out["obv"] = self._obv(close, volume)
        out["obv_slope_5"] = out["obv"].diff(5) / 5
        out["obv_trend_positive"] = (out["obv_slope_5"] > 0).astype(bool)

        adx_frame = self._adx(high, low, close, 14)
        out["adx"] = adx_frame["adx"]
        out["plus_di"] = adx_frame["plus_di"]
        out["minus_di"] = adx_frame["minus_di"]

        out["volume_sma_20"] = volume.rolling(window=20, min_periods=20).mean()
        out["volume_above_sma_20"] = (volume > out["volume_sma_20"]).astype(bool)

        return out

    def latest_indicator_snapshot(self, df: pd.DataFrame) -> dict:
        """Return the latest row's indicator values as a clean dictionary."""
        enriched = df if set(self.INDICATOR_COLUMNS).issubset(df.columns) else self.add_indicators(df)
        latest = enriched.sort_values("timestamp", ascending=True).iloc[-1]
        snapshot = {
            "timestamp": latest["timestamp"],
            "symbol": latest["symbol"],
            "exchange_symbol": latest["exchange_symbol"],
            "close": float(latest["close"]),
        }
        for column in self.INDICATOR_COLUMNS:
            value = latest[column]
            if isinstance(value, (bool, np.bool_)):
                snapshot[column] = bool(value)
            elif pd.isna(value):
                snapshot[column] = None
            else:
                snapshot[column] = float(value)
        return snapshot

    def _ema(self, series: pd.Series, span: int) -> pd.Series:
        """Calculate exponential moving average."""
        return series.ewm(span=span, adjust=False, min_periods=span).mean()

    def _rsi(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate relative strength index."""
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(100).where(avg_loss != 0, 100)

    def _atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        """Calculate average true range."""
        previous_close = close.shift(1)
        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    def _obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate on-balance volume."""
        direction = np.sign(close.diff()).fillna(0)
        return (direction * volume).cumsum().astype(float)

    def _adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.DataFrame:
        """Calculate ADX, plus DI, and minus DI."""
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)

        atr = self._atr(high, low, close, period)
        plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr.replace(0, np.nan)
        minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr.replace(0, np.nan)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        return pd.DataFrame({"adx": adx, "plus_di": plus_di, "minus_di": minus_di})
