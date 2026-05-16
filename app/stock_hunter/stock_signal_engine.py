"""Read-only stock/ETF signal placeholder scoring."""

from __future__ import annotations

from app.stock_hunter.stock_hunter_models import StockSignalResult


class StockSignalEngine:
    """Small transparent stock signal scorer for future Stock/Options Hunter work."""

    def score(self, symbol: str, quote: dict | None = None, candles: list[dict] | None = None) -> StockSignalResult:
        """Score provided quote/candle data without fetching or trading."""
        normalized = symbol.strip().upper()
        reasons: list[str] = []
        warnings: list[str] = []
        blockers: list[str] = []
        score = 0
        latest_price = self._latest_price(quote, candles)

        if latest_price is None:
            blockers.append("stock quote or candle data unavailable")
            return StockSignalResult(normalized, 0, "AVOID", reasons, warnings, blockers, None, "DATA_UNAVAILABLE", "DATA_UNAVAILABLE")

        score += 30
        reasons.append("price data available")
        trend_status = "NEUTRAL"
        volume_status = "UNKNOWN"

        moving_average = self._value(quote, "moving_average") or self._average_close(candles)
        if moving_average is not None:
            if latest_price > moving_average:
                score += 25
                trend_status = "BULLISH"
                reasons.append("price above moving average")
            else:
                score += 5
                trend_status = "BEARISH"
                warnings.append("price below moving average")
        else:
            warnings.append("moving average unavailable")

        volume = self._value(quote, "volume")
        avg_volume = self._value(quote, "avg_volume")
        if volume is not None and avg_volume is not None and avg_volume > 0:
            if volume >= avg_volume:
                score += 20
                volume_status = "ABOVE_AVERAGE"
                reasons.append("volume above average")
            else:
                score += 5
                volume_status = "BELOW_AVERAGE"
                warnings.append("volume below average")
        else:
            warnings.append("volume comparison unavailable")

        momentum = self._value(quote, "momentum")
        if momentum is not None:
            if momentum > 0:
                score += 25
                reasons.append("positive momentum")
            elif momentum < 0:
                warnings.append("negative momentum")
        else:
            warnings.append("momentum unavailable")

        score = min(score, 100)
        return StockSignalResult(normalized, score, self._category(score), reasons, warnings, blockers, latest_price, trend_status, volume_status)

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
            value = self._value(quote, "latest_price") or self._value(quote, "last_price") or self._value(quote, "last")
            if value is not None and value > 0:
                return value
        if candles:
            value = self._value(candles[-1], "close")
            if value is not None and value > 0:
                return value
        return None

    def _average_close(self, candles: list[dict] | None) -> float | None:
        """Calculate average close from provided candles."""
        if not candles:
            return None
        closes = [self._value(candle, "close") for candle in candles]
        valid = [close for close in closes if close is not None]
        return sum(valid) / len(valid) if valid else None

    def _value(self, data: dict | None, key: str) -> float | None:
        """Read optional float value."""
        if not data:
            return None
        value = data.get(key)
        if value is None:
            return None
        return float(value)
