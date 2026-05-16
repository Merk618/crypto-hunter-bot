"""Read-only Stock/Options Hunter signal scoring."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from statistics import fmean

from app.config import Settings, get_settings
from app.stock_hunter.stock_hunter_models import StockSignalResult


class StockSignalEngine:
    """Transparent stock/ETF scorer using read-only quote, candle, and option data."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize scoring thresholds."""
        self.settings = settings or get_settings()

    def score(
        self,
        symbol: str,
        quote: dict | None = None,
        candles: list[dict] | None = None,
        options_analysis: dict | None = None,
        market_state: dict | None = None,
    ) -> StockSignalResult:
        """Score provided read-only data without fetching, trading, or execution."""
        normalized = symbol.strip().upper()
        reasons: list[str] = []
        warnings: list[str] = []
        blockers: list[str] = []
        latest_price = self._latest_price(quote, candles)
        features = self._features(quote, candles, latest_price)

        if latest_price is None:
            blockers.append("stock quote or candle data unavailable")
            return StockSignalResult(
                symbol=normalized,
                score=0,
                raw_score=0,
                category="AVOID",
                reasons=reasons,
                warnings=warnings,
                blockers=blockers,
                latest_price=None,
                trend_status="DATA_UNAVAILABLE",
                volume_status="DATA_UNAVAILABLE",
                momentum_status="DATA_UNAVAILABLE",
                options_status="DATA_UNAVAILABLE",
                component_scores={"trend": 0, "momentum": 0, "volume_liquidity": 0, "market_quality": 0, "options_support": 0},
            )

        trend_score, trend_status = self._score_trend(latest_price, features, reasons, warnings)
        momentum_score, momentum_status, cap_watch = self._score_momentum(features, reasons, warnings)
        volume_score, volume_status = self._score_volume(latest_price, features, reasons, warnings)
        quality_score = self._score_market_quality(latest_price, quote, market_state, features, reasons, warnings, blockers)
        options_score, options_status = self._score_options(options_analysis, reasons, warnings)

        component_scores = {
            "trend": trend_score,
            "momentum": momentum_score,
            "volume_liquidity": volume_score,
            "market_quality": quality_score,
            "options_support": options_score,
        }
        raw_score = int(sum(component_scores.values()))
        score = min(raw_score, 100)
        if cap_watch and score >= self.settings.stock_hunter_strong_score:
            score = self.settings.stock_hunter_strong_score - 1
            warnings.append("RSI overextended; capped at WATCH")

        return StockSignalResult(
            symbol=normalized,
            score=score,
            raw_score=raw_score,
            category=self._category(score),
            reasons=reasons,
            warnings=warnings,
            blockers=blockers,
            latest_price=latest_price,
            trend_status=trend_status,
            volume_status=volume_status,
            momentum_status=momentum_status,
            options_status=options_status,
            component_scores=component_scores,
        )

    def _score_trend(self, close: float, features: dict, reasons: list[str], warnings: list[str]) -> tuple[int, str]:
        """Score trend alignment."""
        score = 0
        bullish_checks = 0
        ema_20 = features.get("ema_20")
        ema_50 = features.get("ema_50")
        ema_200 = features.get("ema_200")

        if ema_200 is not None and close > ema_200:
            score += 10
            bullish_checks += 1
            reasons.append("close above EMA 200")
        elif ema_200 is not None:
            warnings.append("close below EMA 200")

        if ema_50 is not None and close > ema_50:
            score += 7
            bullish_checks += 1
            reasons.append("close above EMA 50")
        if ema_20 is not None and ema_50 is not None and ema_20 > ema_50:
            score += 6
            bullish_checks += 1
            reasons.append("EMA 20 above EMA 50")
        if ema_50 is not None and ema_200 is not None and ema_50 > ema_200:
            score += 4
            bullish_checks += 1
            reasons.append("EMA 50 above EMA 200")
        if ema_20 is not None and close > ema_20:
            score += 3
            bullish_checks += 1
            reasons.append("close above EMA 20")

        if bullish_checks >= 4:
            return score, "BULLISH"
        if bullish_checks >= 2:
            return score, "MIXED"
        return score, "WEAK"

    def _score_momentum(self, features: dict, reasons: list[str], warnings: list[str]) -> tuple[int, str, bool]:
        """Score momentum quality."""
        score = 0
        positives = 0
        cap_watch = False
        rsi = features.get("rsi")
        if rsi is not None:
            if self.settings.stock_hunter_ideal_rsi_min <= rsi <= self.settings.stock_hunter_ideal_rsi_max:
                score += 8
                positives += 1
                reasons.append("RSI in ideal momentum zone")
            elif self.settings.stock_hunter_ideal_rsi_max < rsi < self.settings.stock_hunter_max_extended_rsi:
                score += 4
                positives += 1
                warnings.append("RSI elevated; avoid chasing")
            elif rsi >= self.settings.stock_hunter_max_extended_rsi:
                cap_watch = True
                warnings.append("RSI overextended")
            elif rsi < self.settings.stock_hunter_ideal_rsi_min:
                warnings.append("RSI below preferred momentum zone")
        else:
            warnings.append("RSI unavailable")

        macd_line = features.get("macd_line")
        macd_signal = features.get("macd_signal")
        if macd_line is not None and macd_signal is not None and macd_line > macd_signal:
            score += 8
            positives += 1
            reasons.append("MACD bullish")
        elif macd_line is not None and macd_signal is not None:
            warnings.append("MACD not bullish")

        if (features.get("momentum_5d") or 0) > 0:
            score += 5
            positives += 1
            reasons.append("5-day momentum positive")
        if (features.get("momentum_20d") or 0) > 0:
            score += 4
            positives += 1
            reasons.append("20-day momentum positive")

        if positives >= 3:
            status = "BULLISH"
        elif positives >= 1:
            status = "MIXED"
        else:
            status = "WEAK"
        return score, status, cap_watch

    def _score_volume(self, price: float, features: dict, reasons: list[str], warnings: list[str]) -> tuple[int, str]:
        """Score volume and liquidity."""
        score = 0
        volume = features.get("volume")
        avg_volume = features.get("avg_volume_20")
        if volume is not None and avg_volume is not None and avg_volume > 0:
            if volume > avg_volume:
                score += 7
                reasons.append("volume above 20-period average")
            else:
                warnings.append("volume below 20-period average")
        else:
            warnings.append("volume comparison unavailable")

        if avg_volume is not None and avg_volume >= self.settings.stock_hunter_min_avg_volume:
            score += 6
            reasons.append("average volume meets liquidity floor")
        elif avg_volume is not None:
            warnings.append("average volume below liquidity floor")

        dollar_volume = features.get("dollar_volume")
        if dollar_volume is not None and dollar_volume >= self.settings.stock_hunter_min_avg_volume * max(price, 1):
            score += 4
            reasons.append("dollar volume healthy")

        if price > 5:
            score += 3
            reasons.append("price above low-price risk floor")
        else:
            warnings.append("price below low-price risk floor")

        if score >= 13:
            return score, "HEALTHY"
        if score >= 6:
            return score, "MIXED"
        return score, "THIN"

    def _score_market_quality(self, price: float, quote: dict | None, market_state: dict | None, features: dict, reasons: list[str], warnings: list[str], blockers: list[str]) -> int:
        """Score spread, market state, gap, and data freshness."""
        score = 0
        bid = self._value(quote, "bid")
        ask = self._value(quote, "ask")
        if bid is not None and ask is not None and bid > 0 and ask > 0:
            spread_pct = ((ask - bid) / ((ask + bid) / 2)) * 100
            if spread_pct <= self.settings.stock_hunter_max_bid_ask_spread_pct:
                score += 5
                reasons.append("bid/ask spread acceptable")
            else:
                warnings.append("bid/ask spread wide")

        state = str((market_state or quote or {}).get("market_state", "")).lower()
        if not state or state in {"open", "normal", "regular", "trading"}:
            score += 4
            reasons.append("market state acceptable")
        elif self.settings.stock_hunter_require_market_open:
            blockers.append("market is not open")
        else:
            warnings.append("market state not regular/open")

        previous_close = features.get("previous_close")
        if previous_close and previous_close > 0:
            gap_pct = ((price - previous_close) / previous_close) * 100
            if gap_pct <= 8:
                score += 3
                reasons.append("not an extreme gap up")
            else:
                warnings.append("extreme gap up; avoid chasing")
        else:
            score += 3
            warnings.append("previous close unavailable")

        if self._is_fresh(quote):
            score += 3
            reasons.append("quote data freshness acceptable")
        else:
            warnings.append("quote timestamp unavailable or stale")
        return score

    def _score_options(self, analysis: dict | None, reasons: list[str], warnings: list[str]) -> tuple[int, str]:
        """Score option-chain support without recommending execution."""
        if not analysis:
            warnings.append("options analysis unavailable")
            return 0, "UNAVAILABLE"
        calls = analysis.get("best_call_candidates") or []
        if not calls:
            warnings.append("no liquid call research candidates")
            return 0, "NONE"
        score = 5
        reasons.append("liquid call research candidates available")
        if any(self._value(candidate, "delta") is not None and self.settings.stock_hunter_target_delta_min <= abs(self._value(candidate, "delta") or 0) <= self.settings.stock_hunter_target_delta_max for candidate in calls):
            score += 3
            reasons.append("target-delta call candidates available")
        if any((self._value(candidate, "spread_pct") or 999) <= self.settings.stock_hunter_max_bid_ask_spread_pct for candidate in calls):
            score += 2
            reasons.append("acceptable spread option candidates available")
        return score, "SUPPORTED"

    def _features(self, quote: dict | None, candles: list[dict] | None, latest_price: float | None) -> dict:
        """Build scoring features from quote and candles."""
        closes = [self._value(candle, "close") for candle in candles or []]
        closes = [value for value in closes if value is not None and value > 0]
        volumes = [self._value(candle, "volume") for candle in candles or []]
        volumes = [value for value in volumes if value is not None and value >= 0]
        close = latest_price or (closes[-1] if closes else None)
        avg_volume = self._value(quote, "avg_volume") or self._sma(volumes, 20)
        volume = self._value(quote, "volume") or (volumes[-1] if volumes else None)
        moving_average = self._value(quote, "moving_average")
        return {
            "ema_20": self._value(quote, "ema_20") or self._ema(closes, 20) or moving_average,
            "ema_50": self._value(quote, "ema_50") or self._ema(closes, 50) or moving_average,
            "ema_200": self._value(quote, "ema_200") or self._ema(closes, 200) or moving_average,
            "rsi": self._value(quote, "rsi") or self._rsi(closes, 14),
            "macd_line": self._value(quote, "macd_line") or self._macd(closes)[0],
            "macd_signal": self._value(quote, "macd_signal") or self._macd(closes)[1],
            "momentum_5d": self._value(quote, "momentum_5d") or self._momentum(closes, 5) or self._value(quote, "momentum"),
            "momentum_20d": self._value(quote, "momentum_20d") or self._momentum(closes, 20),
            "volume": volume,
            "avg_volume_20": avg_volume,
            "dollar_volume": (volume * close) if volume is not None and close is not None else None,
            "previous_close": self._value(quote, "previous_close") or self._value(quote, "prev_close") or (closes[-2] if len(closes) >= 2 else None),
        }

    def _category(self, score: int) -> str:
        """Map score to stock signal category."""
        if score >= 80:
            return "LEADING"
        if score >= 65:
            return "WATCH"
        if score >= 50:
            return "NEUTRAL"
        if score >= 35:
            return "WEAK"
        return "AVOID"

    def _latest_price(self, quote: dict | None, candles: list[dict] | None) -> float | None:
        """Read latest price from quote or candles."""
        if quote:
            for key in ("latest_price", "last_price", "last", "close"):
                value = self._value(quote, key)
                if value is not None and value > 0:
                    return value
        if candles:
            value = self._value(candles[-1], "close")
            if value is not None and value > 0:
                return value
        return None

    def _ema(self, values: list[float], period: int) -> float | None:
        """Return latest EMA value."""
        if not values:
            return None
        alpha = 2 / (period + 1)
        ema = values[0]
        for value in values[1:]:
            ema = (value * alpha) + (ema * (1 - alpha))
        return ema

    def _sma(self, values: list[float], period: int) -> float | None:
        """Return latest simple moving average."""
        if not values:
            return None
        return fmean(values[-period:])

    def _rsi(self, values: list[float], period: int) -> float | None:
        """Return latest RSI."""
        if len(values) <= period:
            return None
        gains: list[float] = []
        losses: list[float] = []
        for previous, current in zip(values[-period - 1 : -1], values[-period:]):
            change = current - previous
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))
        avg_gain = fmean(gains)
        avg_loss = fmean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _macd(self, values: list[float]) -> tuple[float | None, float | None]:
        """Return approximate latest MACD line and signal."""
        if len(values) < 26:
            return None, None
        macd_values: list[float] = []
        for idx in range(26, len(values) + 1):
            window = values[:idx]
            fast = self._ema(window, 12)
            slow = self._ema(window, 26)
            if fast is not None and slow is not None:
                macd_values.append(fast - slow)
        if not macd_values:
            return None, None
        return macd_values[-1], self._ema(macd_values, 9)

    def _momentum(self, values: list[float], periods: int) -> float | None:
        """Return simple percentage momentum."""
        if len(values) <= periods or values[-periods - 1] == 0:
            return None
        return ((values[-1] - values[-periods - 1]) / values[-periods - 1]) * 100

    def _is_fresh(self, quote: dict | None) -> bool:
        """Treat absent timestamps as acceptable for mocked/snapshot data."""
        if not quote or not quote.get("timestamp"):
            return True
        try:
            timestamp = datetime.fromisoformat(str(quote["timestamp"]).replace("Z", "+00:00"))
        except ValueError:
            return False
        age = datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
        return age.total_seconds() <= 900

    def _value(self, data: dict | None, key: str) -> float | None:
        """Read optional finite float value."""
        if not data:
            return None
        value = data.get(key)
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None
