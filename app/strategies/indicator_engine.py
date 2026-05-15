"""Indicator calculation placeholders for Phase 1."""

import pandas as pd


class IndicatorEngine:
    """Compute indicators used by Crypto Hunter strategies."""

    def add_indicators(self, candles: pd.DataFrame) -> pd.DataFrame:
        """Return candles unchanged until strategy indicators are implemented."""
        return candles.copy()
