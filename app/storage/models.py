"""Storage model placeholders for a later phase."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeRecord:
    """Trade record shape placeholder."""

    symbol: str
    side: str
    quantity: float
    price: float | None = None
