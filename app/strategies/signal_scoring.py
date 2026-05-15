"""Transparent signal scoring for Crypto Hunter."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd


class SignalScoringError(ValueError):
    """Base exception for signal scoring failures."""


class MissingIndicatorColumnsError(SignalScoringError):
    """Raised when required indicator columns are absent."""


@dataclass(frozen=True)
class SignalResult:
    """Structured Crypto Hunter signal result."""

    symbol: str
    timeframe: str
    timestamp: Any
    score: int
    category: str
    risk_level: str
    reasons: list[str]
    warnings: list[str]
    blockers: list[str]
    component_scores: dict[str, int]
    latest_price: float
    suggested_entry: float | None
    suggested_stop_loss: float | None
    suggested_take_profit: float | None
    atr: float | None
    exit_watch: bool
    trim_zone: bool
    momentum_warning: str | None
    source: str = "crypto_hunter_signal_v1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return a JSON-friendly dictionary representation."""
        data = asdict(self)
        timestamp = data.get("timestamp")
        if hasattr(timestamp, "isoformat"):
            data["timestamp"] = timestamp.isoformat()
        return data


class SignalScoringEngine:
    """Score indicator-enhanced candle DataFrames deterministically."""

    REQUIRED_COLUMNS = {
        "timestamp",
        "close",
        "volume",
        "symbol",
        "exchange_symbol",
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
    }

    def validate_indicator_dataframe(self, df: pd.DataFrame) -> None:
        """Ensure the DataFrame contains required indicator columns."""
        if df is None or df.empty:
            raise MissingIndicatorColumnsError("Indicator DataFrame is empty")
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise MissingIndicatorColumnsError(f"Missing required indicator columns: {sorted(missing)}")

    def score(self, df: pd.DataFrame, timeframe: str = "1h", symbol: str | None = None) -> SignalResult:
        """Score the latest candle and return a structured signal."""
        self.validate_indicator_dataframe(df)
        data = df.copy().sort_values("timestamp", ascending=True).reset_index(drop=True)
        latest = data.iloc[-1]
        previous = data.iloc[-2] if len(data) >= 2 else latest
        last_three = data.tail(4)

        reasons: list[str] = []
        warnings: list[str] = []
        blockers: list[str] = []

        close = self._as_float(latest["close"])
        volume = self._as_float(latest["volume"])
        atr = self._optional_float(latest["atr_14"])
        adx = self._optional_float(latest["adx"])
        rsi = self._optional_float(latest["rsi_14"])
        macd_line = self._optional_float(latest["macd_line"])
        macd_signal = self._optional_float(latest["macd_signal"])
        macd_histogram = self._optional_float(latest["macd_histogram"])
        bb_upper = self._optional_float(latest["bb_upper"])
        bb_middle = self._optional_float(latest["bb_middle"])
        bb_percent_b = self._optional_float(latest["bb_percent_b"])
        ema_20 = self._optional_float(latest["ema_20"])
        ema_50 = self._optional_float(latest["ema_50"])
        ema_200 = self._optional_float(latest["ema_200"])
        plus_di = self._optional_float(latest["plus_di"])
        minus_di = self._optional_float(latest["minus_di"])
        obv_slope_5 = self._optional_float(latest["obv_slope_5"])

        component_scores = {
            "trend": self._score_trend(close, ema_20, ema_50, ema_200, reasons),
            "momentum": self._score_momentum(rsi, macd_line, macd_signal, macd_histogram, last_three, reasons, warnings, blockers),
            "volume_flow": self._score_volume_flow(volume, latest, obv_slope_5, reasons, blockers),
            "trend_strength": self._score_trend_strength(adx, plus_di, minus_di, data, reasons, blockers),
            "entry_quality": self._score_entry_quality(close, bb_middle, bb_upper, bb_percent_b, atr, reasons, warnings, blockers),
        }
        raw_score = int(sum(component_scores.values()))
        score = raw_score

        if ema_200 is not None and close <= ema_200:
            blockers.append("close at or below EMA 200")
            score = min(score, 64)
        if rsi is not None and rsi >= 75:
            score = min(score, 64)
        if atr is None or atr <= 0:
            blockers.append("ATR missing or invalid")
            warnings.append("ATR unavailable; suggested levels are omitted")
            score = min(score, 49)
        if volume is None or volume <= 0:
            blockers.append("volume missing or zero")
            score = min(score, 49)
        if adx is not None and adx < 15:
            blockers.append("ADX below 15")
        if macd_line is not None and macd_signal is not None and macd_line < macd_signal:
            blockers.append("MACD line below signal")

        category = self._category(score)
        if blockers and raw_score >= 80 and category == "STRONG_BUY":
            category = "BUY_WATCH"

        exit_watch, trim_zone, momentum_warning = self._exit_metadata(latest, previous, data, close, ema_20, bb_upper, rsi, macd_histogram)
        risk_level = self._risk_level(score, adx, rsi, close, ema_200, blockers, atr, volume)

        suggested_entry = close
        suggested_stop_loss = close - (1.5 * atr) if atr is not None and atr > 0 else None
        suggested_take_profit = close + (3.0 * atr) if atr is not None and atr > 0 else None

        return SignalResult(
            symbol=symbol or str(latest["symbol"]),
            timeframe=timeframe,
            timestamp=latest["timestamp"],
            score=int(score),
            category=category,
            risk_level=risk_level,
            reasons=reasons,
            warnings=self._dedupe(warnings),
            blockers=self._dedupe(blockers),
            component_scores={**component_scores, "raw_score": raw_score},
            latest_price=close,
            suggested_entry=suggested_entry,
            suggested_stop_loss=suggested_stop_loss,
            suggested_take_profit=suggested_take_profit,
            atr=atr,
            exit_watch=exit_watch,
            trim_zone=trim_zone,
            momentum_warning=momentum_warning,
            metadata={
                "rsi_interpretation": self._rsi_interpretation(rsi),
                "raw_score_before_caps": raw_score,
            },
        )

    def _score_trend(self, close: float, ema_20: float | None, ema_50: float | None, ema_200: float | None, reasons: list[str]) -> int:
        """Score trend alignment, max 25 points."""
        score = 0
        if ema_200 is not None and close > ema_200:
            score += 12
            reasons.append("close above EMA 200")
        if ema_20 is not None and ema_50 is not None and ema_20 > ema_50:
            score += 6
            reasons.append("EMA 20 above EMA 50")
        if ema_50 is not None and ema_200 is not None and ema_50 > ema_200:
            score += 4
            reasons.append("EMA 50 above EMA 200")
        if ema_20 is not None and close > ema_20:
            score += 3
            reasons.append("close above EMA 20")
        return score

    def _score_momentum(
        self,
        rsi: float | None,
        macd_line: float | None,
        macd_signal: float | None,
        macd_histogram: float | None,
        last_three: pd.DataFrame,
        reasons: list[str],
        warnings: list[str],
        blockers: list[str],
    ) -> int:
        """Score momentum, max 25 points."""
        score = 0
        if macd_line is not None and macd_signal is not None and macd_line > macd_signal:
            score += 8
            reasons.append("MACD line above signal")
        if macd_histogram is not None and macd_histogram > 0:
            score += 5
            reasons.append("MACD histogram positive")
        if len(last_three) >= 4 and last_three["macd_histogram"].iloc[-1] > last_three["macd_histogram"].iloc[-4]:
            score += 4
            reasons.append("MACD histogram increasing over last 3 candles")
        if rsi is None:
            warnings.append("RSI unavailable")
            return score
        if 40 <= rsi <= 60:
            score += 8
            reasons.append("RSI in ideal bullish momentum zone 40-60")
        elif 35 <= rsi < 40 or 60 < rsi <= 65:
            score += 4
            reasons.append("RSI in acceptable bullish momentum zone 35-65")
        elif 65 < rsi < 70:
            score += 2
            warnings.append("RSI elevated; avoid chasing")
        elif rsi < 40:
            warnings.append("RSI below 40; bullish momentum reduced")
        if rsi >= 70:
            warnings.append("RSI overbought warning; trim/watch zone, not automatic sell")
        if rsi >= 75:
            blockers.append("RSI >= 75 hard caution")
        if rsi <= 30:
            warnings.append("RSI oversold; falling-knife risk unless reversal confirmation exists")
        return score

    def _score_volume_flow(self, volume: float | None, latest: pd.Series, obv_slope_5: float | None, reasons: list[str], blockers: list[str]) -> int:
        """Score volume and flow, max 20 points."""
        score = 0
        if bool(latest["volume_above_sma_20"]):
            score += 7
            reasons.append("volume above SMA 20")
        if bool(latest["obv_trend_positive"]):
            score += 7
            reasons.append("OBV trend positive")
        if obv_slope_5 is not None and obv_slope_5 > 0:
            score += 3
            reasons.append("OBV slope positive")
        if volume is not None and volume > 0:
            score += 3
            reasons.append("volume present")
        else:
            blockers.append("volume missing or zero")
        return score

    def _score_trend_strength(self, adx: float | None, plus_di: float | None, minus_di: float | None, data: pd.DataFrame, reasons: list[str], blockers: list[str]) -> int:
        """Score trend strength, max 15 points."""
        score = 0
        if adx is None:
            blockers.append("ADX missing")
            return score
        if adx >= 25:
            score += 8
            reasons.append("ADX >= 25")
        elif 20 <= adx < 25:
            score += 4
            reasons.append("ADX between 20 and 25")
        if plus_di is not None and minus_di is not None and plus_di > minus_di:
            score += 5
            reasons.append("plus DI above minus DI")
        if len(data) >= 4 and data["adx"].iloc[-1] > data["adx"].iloc[-4]:
            score += 2
            reasons.append("ADX rising over last 3 candles")
        return score

    def _score_entry_quality(
        self,
        close: float,
        bb_middle: float | None,
        bb_upper: float | None,
        bb_percent_b: float | None,
        atr: float | None,
        reasons: list[str],
        warnings: list[str],
        blockers: list[str],
    ) -> int:
        """Score entry quality, max 15 points."""
        score = 0
        if bb_percent_b is not None and 0.20 <= bb_percent_b <= 0.80:
            score += 5
            reasons.append("Bollinger percent B in balanced entry range")
        if bb_upper is not None and close <= bb_upper:
            score += 4
            reasons.append("close not above upper Bollinger Band")
        if bb_middle is not None and close > bb_middle:
            score += 3
            reasons.append("close above Bollinger middle band")
        if atr is not None and atr > 0:
            score += 3
            reasons.append("ATR valid")
        else:
            blockers.append("ATR missing or invalid")
            warnings.append("ATR unavailable; suggested levels are omitted")
        return score

    def _exit_metadata(
        self,
        latest: pd.Series,
        previous: pd.Series,
        data: pd.DataFrame,
        close: float,
        ema_20: float | None,
        bb_upper: float | None,
        rsi: float | None,
        macd_histogram: float | None,
    ) -> tuple[bool, bool, str | None]:
        """Build advisory-only exit metadata."""
        prev_rsi = self._optional_float(previous["rsi_14"])
        macd_weakening = len(data) >= 4 and data["macd_histogram"].iloc[-1] < data["macd_histogram"].iloc[-4]
        near_upper_band = bb_upper is not None and close >= bb_upper * 0.995
        exit_watch = bool((rsi is not None and rsi >= 70) or macd_weakening)
        trim_zone = bool((rsi is not None and 70 <= rsi < 75) or near_upper_band)

        messages: list[str] = []
        if prev_rsi is not None and rsi is not None and prev_rsi > 70 and rsi < 70:
            messages.append("RSI crossing down from above 70; sell/trim warning")
        if rsi is not None and rsi < 60 and data["rsi_14"].tail(12).max() > 70:
            messages.append("RSI crossed below 60 after overbought; stronger momentum-exit warning")
        if rsi is not None and rsi < 50:
            messages.append("RSI below 50; bullish momentum weakening")
        if rsi is not None and rsi < 40:
            messages.append("RSI below 40; bearish momentum")
        if macd_weakening:
            messages.append("MACD histogram weakening")
        if ema_20 is not None and close < ema_20:
            messages.append("price losing EMA 20")
        if not messages and rsi is not None and 70 <= rsi < 75:
            messages.append("RSI 70-75; trim/watch/tighten stop if MACD weakens")
        return exit_watch, trim_zone, "; ".join(messages) if messages else None

    def _risk_level(self, score: int, adx: float | None, rsi: float | None, close: float, ema_200: float | None, blockers: list[str], atr: float | None, volume: float | None) -> str:
        """Assign a risk level from score and blockers."""
        if score < 50 or atr is None or atr <= 0 or volume is None or volume <= 0:
            return "EXTREME"
        if score >= 80 and adx is not None and adx >= 25 and rsi is not None and rsi < 68 and ema_200 is not None and close > ema_200 and not blockers:
            return "LOW"
        if 65 <= score <= 79 and not blockers:
            return "MEDIUM"
        return "HIGH"

    def _category(self, score: int) -> str:
        """Convert numeric score into signal category."""
        if score >= 80:
            return "STRONG_BUY"
        if score >= 65:
            return "BUY_WATCH"
        if score >= 50:
            return "NEUTRAL"
        if score >= 35:
            return "WEAK"
        return "AVOID_SELL"

    def _rsi_interpretation(self, rsi: float | None) -> str:
        """Describe RSI zone interpretation."""
        if rsi is None:
            return "RSI unavailable"
        if rsi < 30:
            return "oversold with falling-knife risk"
        if rsi < 40:
            return "early recovery or weak momentum"
        if rsi <= 60:
            return "ideal bullish momentum zone"
        if rsi <= 65:
            return "strong but slightly extended"
        if rsi < 70:
            return "elevated; avoid chasing"
        if rsi < 75:
            return "overbought warning; trim/watch zone"
        return "hard caution; cap long-entry score"

    def _as_float(self, value: Any) -> float:
        """Convert a required numeric value to float."""
        return float(value)

    def _optional_float(self, value: Any) -> float | None:
        """Convert optional numeric values, returning None for NaN."""
        if pd.isna(value):
            return None
        converted = float(value)
        if not np.isfinite(converted):
            return None
        return converted

    def _dedupe(self, values: list[str]) -> list[str]:
        """Return values without duplicates while preserving order."""
        return list(dict.fromkeys(values))
