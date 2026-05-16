"""MooMoo stock symbol mapping."""

from __future__ import annotations

import re


class MooMooSymbolError(ValueError):
    """Raised when a symbol cannot be mapped safely."""


class MooMooSymbolMapper:
    """Map common stock symbols into MooMoo provider symbols."""

    STOCK_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
    PROVIDER_RE = re.compile(r"^[A-Z]{2}\.[A-Z][A-Z0-9.\-]{0,9}$")
    CRYPTO_MARKERS = {"/", "BTC", "ETH", "SOL", "XRP", "LINK", "AVAX", "SUI"}

    def __init__(self, default_region: str = "US") -> None:
        """Initialize mapper."""
        self.default_region = default_region.strip().upper() or "US"

    def to_provider_symbol(self, symbol: str) -> str:
        """Convert a user stock symbol to MooMoo provider format."""
        normalized = symbol.strip().upper()
        if self._looks_crypto(normalized):
            raise MooMooSymbolError(f"Crypto symbols are not valid for MooMoo Stock Hunter: {symbol}")
        if self.PROVIDER_RE.match(normalized):
            return normalized
        if not self.STOCK_RE.match(normalized):
            raise MooMooSymbolError(f"Invalid stock symbol: {symbol}")
        return f"{self.default_region}.{normalized}"

    def to_user_symbol(self, provider_symbol: str) -> str:
        """Convert provider symbol to common user symbol."""
        normalized = self.to_provider_symbol(provider_symbol)
        return normalized.split(".", maxsplit=1)[1]

    def _looks_crypto(self, symbol: str) -> bool:
        """Return True for obvious crypto pair symbols."""
        if "/" in symbol:
            return True
        base = symbol.split(".", maxsplit=1)[-1]
        return base in self.CRYPTO_MARKERS
