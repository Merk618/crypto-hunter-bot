"""Read-only Stock/Options Hunter service."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_market_data import MooMooMarketData
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.stock_hunter.options_chain_analyzer import OptionsChainAnalyzer
from app.stock_hunter.stock_scanner import StockScanner
from app.stock_hunter.stock_signal_engine import StockSignalEngine
from app.stock_hunter.stock_watchlist import StockWatchlist


class StockHunterService:
    """Facade for Stock/Options Hunter read-only endpoints."""

    def __init__(
        self,
        settings: Settings | None = None,
        watchlist: StockWatchlist | None = None,
        moomoo_client: MooMooReadOnlyClient | None = None,
        market_data: MooMooMarketData | None = None,
        scanner: StockScanner | None = None,
        options_analyzer: OptionsChainAnalyzer | None = None,
    ) -> None:
        """Initialize service."""
        self.settings = settings or get_settings()
        self.watchlist = watchlist or StockWatchlist(settings=self.settings)
        self.market_data = market_data or MooMooMarketData(settings=self.settings)
        self.moomoo_client = moomoo_client or MooMooReadOnlyClient(settings=self.settings, market_data=self.market_data)
        self.options_analyzer = options_analyzer or OptionsChainAnalyzer(settings=self.settings)
        self.scanner = scanner or StockScanner(self.moomoo_client, StockSignalEngine(), self.options_analyzer)

    def get_status(self) -> dict:
        """Return read-only service status."""
        return {
            "enabled": self.settings.stock_hunter_enabled,
            "read_only": self.settings.stock_hunter_read_only,
            "trading_allowed": False,
            "options_analysis_enabled": self.settings.stock_hunter_enable_options_analysis,
            "moomoo_health": self.moomoo_client.get_health().to_dict(),
            "source": "stock_hunter_status_v1",
        }

    def get_watchlist(self) -> dict:
        """Return watchlist."""
        return self.watchlist.to_dict()

    def scan_watchlist(self) -> dict:
        """Scan active watchlist symbols without trading."""
        results = [result.to_dict() for result in self.scanner.scan(self.watchlist.get_active_symbols())]
        return {"results": results, "trading_allowed": False, "source": "stock_hunter_scan_v2"}

    def analyze_symbol(self, symbol: str) -> dict:
        """Analyze one symbol without trading."""
        return self.scanner.scan_symbol(symbol).to_dict()

    def analyze_options(self, symbol: str) -> dict:
        """Analyze options for one symbol without execution."""
        if not self.settings.stock_hunter_enable_options_analysis:
            return {"underlying": symbol.upper(), "available": False, "message": "Options analysis disabled"}
        chain = self.moomoo_client.get_option_chain(symbol.upper())
        return self.options_analyzer.analyze(symbol.upper(), chain.get("contracts", [])).to_dict()

    def top_candidates(self, limit: int = 10) -> dict:
        """Return ranked read-only research candidates."""
        results = [result.to_dict() for result in self.scanner.scan(self.watchlist.get_active_symbols())]
        return {
            "results": results[:limit],
            "trading_allowed": False,
            "execution_enabled": False,
            "source": "stock_hunter_top_candidates_v1",
        }
