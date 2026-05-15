"""Crypto Hunter strategy shell."""

from app.strategies.signal_scoring import SignalScore, SignalScorer


class CryptoHunterStrategy:
    """Phase 1 strategy facade."""

    def __init__(self, scorer: SignalScorer | None = None) -> None:
        """Initialize strategy dependencies."""
        self.scorer = scorer or SignalScorer()

    def evaluate(self, symbol: str) -> SignalScore:
        """Evaluate a symbol and return a neutral Phase 1 signal."""
        return self.scorer.score(symbol)
