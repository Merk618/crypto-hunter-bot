"""Signal scoring tests with synthetic indicator DataFrames."""

import pandas as pd
import pytest

from app.strategies.signal_scoring import MissingIndicatorColumnsError, SignalScoringEngine


def indicator_df(rows: int = 8, **overrides) -> pd.DataFrame:
    """Build deterministic indicator-enhanced candles."""
    data = []
    for i in range(rows):
        row = {
            "timestamp": pd.Timestamp("2026-01-01T00:00:00Z") + pd.Timedelta(hours=i),
            "close": 120.0 + i,
            "volume": 1000.0,
            "symbol": "BTC/USD",
            "exchange_symbol": "XXBTZUSD",
            "ema_20": 110.0 + i,
            "ema_50": 100.0 + i,
            "ema_200": 90.0 + i,
            "rsi_14": 50.0,
            "macd_line": 2.0,
            "macd_signal": 1.0,
            "macd_histogram": 0.5 + (i * 0.1),
            "bb_middle": 115.0 + i,
            "bb_upper": 130.0 + i,
            "bb_lower": 100.0 + i,
            "bb_percent_b": 0.65,
            "atr_14": 4.0,
            "obv": 10000.0 + (i * 100),
            "obv_slope_5": 20.0,
            "obv_trend_positive": True,
            "adx": 26.0 + (i * 0.1),
            "plus_di": 30.0,
            "minus_di": 15.0,
            "volume_sma_20": 900.0,
            "volume_above_sma_20": True,
        }
        data.append(row)
    df = pd.DataFrame(data)
    for key, value in overrides.items():
        df.loc[df.index[-1], key] = value
    return df


def test_strong_bullish_setup_returns_strong_buy_or_buy_watch() -> None:
    """A strong setup returns a bullish category."""
    result = SignalScoringEngine().score(indicator_df())
    assert result.category in {"STRONG_BUY", "BUY_WATCH"}
    assert result.score >= 65


def test_bearish_setup_returns_weak_or_avoid_sell() -> None:
    """A bearish setup returns a weak category."""
    df = indicator_df(
        close=80.0,
        ema_20=95.0,
        ema_50=100.0,
        ema_200=120.0,
        rsi_14=35.0,
        macd_line=-2.0,
        macd_signal=1.0,
        macd_histogram=-1.0,
        volume_above_sma_20=False,
        obv_trend_positive=False,
        obv_slope_5=-10.0,
        adx=12.0,
        plus_di=10.0,
        minus_di=30.0,
        bb_middle=95.0,
        bb_upper=110.0,
        bb_percent_b=0.1,
    )
    result = SignalScoringEngine().score(df)
    assert result.category in {"WEAK", "AVOID_SELL"}


def test_close_below_ema_200_caps_score_at_64() -> None:
    """Close below EMA 200 caps score."""
    result = SignalScoringEngine().score(indicator_df(close=80.0, ema_200=100.0))
    assert result.score <= 64
    assert "close at or below EMA 200" in result.blockers


def test_rsi_40_to_60_gets_strongest_rsi_momentum_score() -> None:
    """RSI 40-60 earns stronger score than 60-65."""
    ideal = SignalScoringEngine().score(indicator_df(rsi_14=50.0))
    acceptable = SignalScoringEngine().score(indicator_df(rsi_14=62.0))
    assert ideal.component_scores["momentum"] - acceptable.component_scores["momentum"] == 4


def test_rsi_65_to_70_adds_elevated_warning_without_hard_blocker() -> None:
    """RSI 65-70 warns but does not block."""
    result = SignalScoringEngine().score(indicator_df(rsi_14=67.0))
    assert "RSI elevated; avoid chasing" in result.warnings
    assert not any("RSI >= 75" in blocker for blocker in result.blockers)


def test_rsi_70_or_above_adds_overbought_warning() -> None:
    """RSI >=70 adds overbought metadata."""
    result = SignalScoringEngine().score(indicator_df(rsi_14=72.0))
    assert any("overbought" in warning for warning in result.warnings)
    assert result.exit_watch is True
    assert result.trim_zone is True


def test_rsi_75_caps_score_and_adds_blocker() -> None:
    """RSI >=75 caps long-entry score and blocks."""
    result = SignalScoringEngine().score(indicator_df(rsi_14=76.0))
    assert result.score <= 64
    assert "RSI >= 75 hard caution" in result.blockers


def test_missing_atr_column_raises_clean_error() -> None:
    """Missing ATR column raises a custom error."""
    df = indicator_df().drop(columns=["atr_14"])
    with pytest.raises(MissingIndicatorColumnsError):
        SignalScoringEngine().score(df)


def test_invalid_atr_caps_score() -> None:
    """Invalid ATR caps score and omits levels."""
    result = SignalScoringEngine().score(indicator_df(atr_14=0.0))
    assert result.score <= 49
    assert result.suggested_stop_loss is None
    assert result.suggested_take_profit is None


def test_missing_required_indicator_columns_raises_clean_custom_error() -> None:
    """Missing indicator columns do not produce KeyError."""
    df = indicator_df().drop(columns=["macd_line"])
    with pytest.raises(MissingIndicatorColumnsError):
        SignalScoringEngine().score(df)


def test_component_scores_sum_to_raw_score_before_caps() -> None:
    """Component scores add up to the raw score before caps."""
    result = SignalScoringEngine().score(indicator_df(rsi_14=76.0))
    component_sum = sum(value for key, value in result.component_scores.items() if key != "raw_score")
    assert component_sum == result.component_scores["raw_score"]
    assert result.component_scores["raw_score"] >= result.score


def test_signal_result_contains_required_explanation_fields() -> None:
    """SignalResult includes explanations and advisory metadata."""
    result = SignalScoringEngine().score(indicator_df(rsi_14=72.0))
    assert result.reasons
    assert result.warnings
    assert isinstance(result.blockers, list)
    assert result.component_scores
    assert isinstance(result.exit_watch, bool)
    assert isinstance(result.trim_zone, bool)
    assert "momentum_warning" in result.to_dict()
