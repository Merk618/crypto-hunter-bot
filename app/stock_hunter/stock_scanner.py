"""Read-only Stock/Options Hunter scanner."""

from __future__ import annotations

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.stock_hunter.options_chain_analyzer import OptionsChainAnalyzer
from app.stock_hunter.stock_hunter_models import StockScannerResult
from app.stock_hunter.stock_signal_engine import StockSignalEngine


class StockScanner:
    """Scan watchlist symbols using read-only data sources."""

    def __init__(self, moomoo_client: MooMooReadOnlyClient | None = None, signal_engine: StockSignalEngine | None = None, options_analyzer: OptionsChainAnalyzer | None = None) -> None:
        """Initialize scanner."""
        self.moomoo_client = moomoo_client or MooMooReadOnlyClient()
        self.signal_engine = signal_engine or StockSignalEngine()
        self.options_analyzer = options_analyzer or OptionsChainAnalyzer()

    def scan(self, symbols: list[str]) -> list[StockScannerResult]:
        """Scan symbols without trading."""
        return [self.scan_symbol(symbol) for symbol in symbols]

    def scan_symbol(self, symbol: str) -> StockScannerResult:
        """Scan one symbol and return a read-only result."""
        normalized = symbol.strip().upper()
        warnings: list[str] = []
        blockers: list[str] = []
        notes: list[str] = ["read-only stock scanner"]

        health = self.moomoo_client.get_health()
        if not health.enabled:
            warnings.append("MooMoo connector disabled")
        if not self.moomoo_client.is_available():
            blockers.append("MooMoo read-only data unavailable")
            signal = self.signal_engine.score(normalized)
            return StockScannerResult(normalized, signal.to_dict(), None, "NO_ACTION", notes, warnings, blockers)

        quote = self.moomoo_client.get_quote_snapshot(normalized)
        if not quote.get("available"):
            blockers.append(quote.get("message", "MooMoo quote unavailable"))
            signal = self.signal_engine.score(normalized)
            return StockScannerResult(normalized, signal.to_dict(), None, "NO_ACTION", notes, warnings, blockers)
        candles_response = self.moomoo_client.get_historical_candles(normalized, "1d", 50)
        candles = candles_response.get("candles", []) if candles_response.get("available") else []
        signal = self.signal_engine.score(normalized, quote=quote, candles=candles)
        options = self.moomoo_client.get_option_chain(normalized)
        analysis = self.options_analyzer.analyze(normalized, options.get("contracts", []))
        return StockScannerResult(normalized, signal.to_dict(), analysis.to_dict(), "RESEARCH_ONLY", notes, warnings, blockers)
