"""Indicator engine tests using synthetic candles."""

import numpy as np
import pandas as pd
import pytest

from app.strategies.indicator_engine import (
    EmptyCandleDataFrameError,
    IndicatorEngine,
    InvalidNumericCandleValuesError,
    MissingCandleColumnsError,
    NotEnoughCandleDataError,
)


def synthetic_candles(rows: int = 260) -> pd.DataFrame:
    """Build deterministic synthetic OHLCV candles."""
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    trend = np.linspace(100, 160, rows)
    wave = np.sin(np.arange(rows) / 5) * 2
    close = trend + wave
    open_ = close - 0.5
    high = close + 1.5
    low = close - 1.5
    volume = 1000 + (np.arange(rows) % 20) * 25
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "vwap": (high + low + close) / 3,
            "volume": volume.astype(float),
            "count": np.arange(rows) + 1,
            "symbol": "BTC/USD",
            "exchange_symbol": "XXBTZUSD",
        }
    )


def test_rejects_empty_dataframe() -> None:
    """Indicator engine rejects empty DataFrames."""
    with pytest.raises(EmptyCandleDataFrameError):
        IndicatorEngine().validate_candle_dataframe(pd.DataFrame())


def test_rejects_missing_required_columns() -> None:
    """Indicator engine rejects missing columns."""
    df = synthetic_candles().drop(columns=["close"])
    with pytest.raises(MissingCandleColumnsError):
        IndicatorEngine().validate_candle_dataframe(df)


def test_rejects_too_few_candles_for_ema_200() -> None:
    """Indicator engine requires enough data for EMA 200."""
    with pytest.raises(NotEnoughCandleDataError):
        IndicatorEngine().validate_candle_dataframe(synthetic_candles(199))


def test_rejects_invalid_numeric_values() -> None:
    """Indicator engine rejects invalid OHLCV numeric values."""
    df = synthetic_candles()
    df["close"] = df["close"].astype(object)
    df.loc[10, "close"] = "bad"
    with pytest.raises(InvalidNumericCandleValuesError):
        IndicatorEngine().validate_candle_dataframe(df)


def test_add_indicators_does_not_mutate_original_dataframe() -> None:
    """add_indicators returns a copy and leaves input untouched."""
    engine = IndicatorEngine()
    df = synthetic_candles()
    original_columns = list(df.columns)
    enriched = engine.add_indicators(df)
    assert list(df.columns) == original_columns
    assert "ema_20" not in df.columns
    assert "ema_20" in enriched.columns


def test_add_indicators_adds_all_required_columns() -> None:
    """add_indicators adds every Phase 3 indicator column."""
    enriched = IndicatorEngine().add_indicators(synthetic_candles())
    for column in IndicatorEngine.INDICATOR_COLUMNS:
        assert column in enriched.columns


def test_rsi_values_are_between_0_and_100_after_warmup() -> None:
    """RSI remains in expected range after warmup."""
    enriched = IndicatorEngine().add_indicators(synthetic_candles())
    rsi = enriched["rsi_14"].iloc[20:].dropna()
    assert ((rsi >= 0) & (rsi <= 100)).all()


def test_bollinger_upper_is_greater_than_lower_after_warmup() -> None:
    """Bollinger bands are ordered after warmup."""
    enriched = IndicatorEngine().add_indicators(synthetic_candles())
    warmed = enriched.iloc[20:].dropna(subset=["bb_upper", "bb_lower"])
    assert (warmed["bb_upper"] > warmed["bb_lower"]).all()


def test_macd_columns_exist_and_are_numeric_after_warmup() -> None:
    """MACD columns contain numeric values after warmup."""
    enriched = IndicatorEngine().add_indicators(synthetic_candles())
    warmed = enriched.iloc[60:]
    for column in ["macd_line", "macd_signal", "macd_histogram"]:
        assert pd.api.types.is_numeric_dtype(warmed[column])
        assert warmed[column].notna().all()


def test_atr_is_non_negative_after_warmup() -> None:
    """ATR is non-negative after warmup."""
    enriched = IndicatorEngine().add_indicators(synthetic_candles())
    atr = enriched["atr_14"].iloc[20:].dropna()
    assert (atr >= 0).all()


def test_obv_column_exists() -> None:
    """OBV column is present."""
    enriched = IndicatorEngine().add_indicators(synthetic_candles())
    assert "obv" in enriched.columns


def test_adx_columns_exist() -> None:
    """ADX columns are present."""
    enriched = IndicatorEngine().add_indicators(synthetic_candles())
    assert {"adx", "plus_di", "minus_di"}.issubset(enriched.columns)


def test_latest_indicator_snapshot_returns_dictionary() -> None:
    """latest_indicator_snapshot returns clean latest indicator values."""
    snapshot = IndicatorEngine().latest_indicator_snapshot(synthetic_candles())
    assert isinstance(snapshot, dict)
    assert snapshot["symbol"] == "BTC/USD"
    assert "ema_20" in snapshot
    assert "rsi_14" in snapshot
    assert "volume_above_sma_20" in snapshot
    assert isinstance(snapshot["volume_above_sma_20"], bool)
