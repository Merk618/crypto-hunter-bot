"""Crypto Hunter signal-only strategy wrapper."""

import pandas as pd

from app.strategies.indicator_engine import IndicatorEngine
from app.strategies.signal_scoring import SignalResult, SignalScoringEngine


class CryptoHunterStrategy:
    """Run indicators and transparent signal scoring for raw candles."""

    def __init__(self, indicator_engine: IndicatorEngine | None = None, scoring_engine: SignalScoringEngine | None = None) -> None:
        """Initialize strategy dependencies."""
        self.indicator_engine = indicator_engine or IndicatorEngine()
        self.scoring_engine = scoring_engine or SignalScoringEngine()

    def evaluate(self, candles: pd.DataFrame, symbol: str, timeframe: str = "1h") -> SignalResult:
        """Add indicators to raw candles and return a structured signal."""
        enriched = self.indicator_engine.add_indicators(candles)
        return self.scoring_engine.score(enriched, timeframe=timeframe, symbol=symbol)
