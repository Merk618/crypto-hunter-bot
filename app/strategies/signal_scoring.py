"""Signal scoring primitives."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalScore:
    """Directional signal score."""

    symbol: str
    direction: str
    confidence: float


class SignalScorer:
    """Score candidate trading signals."""

    def score(self, symbol: str) -> SignalScore:
        """Return a neutral score for Phase 1."""
        return SignalScore(symbol=symbol, direction="hold", confidence=0.0)
