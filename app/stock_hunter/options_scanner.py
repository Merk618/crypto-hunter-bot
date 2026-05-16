"""Dedicated read-only options scanner."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.stock_hunter.options_chain_analyzer import OptionsChainAnalyzer
from app.stock_hunter.options_ranking import OptionsRankingEngine
from app.stock_hunter.options_strategy_models import OptionsScanRequest, OptionsScanResult
from app.stock_hunter.stock_signal_engine import StockSignalEngine
from app.stock_hunter.stock_watchlist import StockWatchlist


class OptionsScanner:
    """Scan and rank option contracts using read-only market data."""

    def __init__(
        self,
        settings: Settings | None = None,
        moomoo_client: MooMooReadOnlyClient | None = None,
        signal_engine: StockSignalEngine | None = None,
        analyzer: OptionsChainAnalyzer | None = None,
        ranking_engine: OptionsRankingEngine | None = None,
    ) -> None:
        """Initialize scanner dependencies."""
        self.settings = settings or get_settings()
        self.moomoo_client = moomoo_client or MooMooReadOnlyClient(settings=self.settings)
        self.signal_engine = signal_engine or StockSignalEngine(settings=self.settings)
        self.analyzer = analyzer or OptionsChainAnalyzer(settings=self.settings)
        self.ranking_engine = ranking_engine or OptionsRankingEngine(settings=self.settings)

    def status(self) -> dict:
        """Return read-only options scanner status."""
        return {
            "enabled": self.settings.options_scanner_enabled,
            "read_only": self.settings.options_scanner_read_only,
            "execution_allowed": False,
            "moomoo_health": self.moomoo_client.get_health().to_dict(),
            "source": "stock_hunter_options_scanner_status_v1",
        }

    def scan_watchlist(self, top_n: int | None = None) -> OptionsScanResult:
        """Scan configured Stock Hunter watchlist symbols."""
        symbols = StockWatchlist(settings=self.settings).get_active_symbols()
        request = OptionsScanRequest(symbols=symbols, top_n=top_n or self.settings.options_scanner_top_n)
        return self.scan(request)

    def scan(self, request: OptionsScanRequest) -> OptionsScanResult:
        """Scan one or more symbols without trading."""
        warnings: list[str] = []
        blockers: list[str] = []
        by_symbol: dict = {}
        all_ranked: list = []
        contracts_analyzed = 0
        rejected_count = 0

        if not self.settings.options_scanner_read_only or self.settings.options_scanner_allow_execution:
            blockers.append("Options scanner execution is disabled by safety policy")
            return self._empty_result(request, warnings, blockers)

        if not self.moomoo_client.is_available():
            blockers.append("MooMoo read-only data unavailable")
            return self._empty_result(request, warnings, blockers)

        for symbol in request.symbols:
            symbol_result = self.scan_symbol(symbol, request)
            by_symbol[symbol] = symbol_result
            contracts_analyzed += symbol_result["contracts_analyzed"]
            rejected_count += symbol_result["rejected_count"]
            all_ranked.extend(symbol_result["ranked_contracts"])

        all_ranked.sort(key=lambda contract: contract.total_score, reverse=True)
        for index, contract in enumerate(all_ranked, start=1):
            contract.rank = index
        top = all_ranked[: int(request.top_n or self.settings.options_scanner_top_n)]
        return OptionsScanResult(
            symbols_scanned=len(request.symbols),
            contracts_analyzed=contracts_analyzed,
            candidates_found=len([contract for contract in all_ranked if contract.label != "REJECTED"]),
            rejected_count=rejected_count,
            top_candidates=[contract.to_dict() for contract in top],
            by_symbol={symbol: self._serialize_symbol_result(result) for symbol, result in by_symbol.items()},
            warnings=warnings,
            blockers=blockers,
        )

    def scan_symbol(self, symbol: str, request: OptionsScanRequest) -> dict:
        """Scan one symbol and return intermediate ranked contracts."""
        normalized = symbol.strip().upper()
        warnings: list[str] = []
        blockers: list[str] = []
        quote = self.moomoo_client.get_quote_snapshot(normalized)
        candles_response = self.moomoo_client.get_historical_candles(normalized, "1d", 250)
        candles = candles_response.get("candles", []) if candles_response.get("available") else []
        signal = self.signal_engine.score(normalized, quote=quote if quote.get("available") else None, candles=candles)
        chain = self.moomoo_client.get_option_chain(normalized)
        contracts = chain.get("contracts", []) if chain.get("available", True) else []
        if not contracts:
            warnings.append("No option contracts available")
        snapshots = [snapshot.to_dict() for snapshot in self.analyzer.normalize_contracts(normalized, contracts)]
        filtered = [contract for contract in snapshots if self._matches_request(contract, request)]
        if not request.include_rejected:
            filtered = [contract for contract in filtered if contract.get("candidate_label") != "REJECTED"]
        rejected_count = len([contract for contract in snapshots if contract.get("candidate_label") == "REJECTED"])
        ranked = self.ranking_engine.rank_contracts(filtered, underlying_score=signal.score)
        return {
            "symbol": normalized,
            "underlying_score": signal.score,
            "contracts_analyzed": len(contracts),
            "rejected_count": rejected_count,
            "ranked_contracts": ranked,
            "warnings": warnings,
            "blockers": blockers,
        }

    def _matches_request(self, contract: dict, request: OptionsScanRequest) -> bool:
        """Return whether a normalized contract matches request filters."""
        option_type = str(contract.get("option_type", "")).lower()
        if request.option_type != "both" and option_type != request.option_type:
            return False
        if (contract.get("volume") or 0) < int(request.min_volume or 0):
            return request.include_rejected
        if (contract.get("open_interest") or 0) < int(request.min_open_interest or 0):
            return request.include_rejected
        spread = contract.get("spread_pct")
        if spread is None or float(spread) > float(request.max_spread_pct or 0):
            return request.include_rejected
        dte = contract.get("dte")
        if dte is None or int(dte) < int(request.min_dte or 0) or int(dte) > int(request.max_dte or 999999):
            return request.include_rejected
        delta = contract.get("delta")
        if delta is None:
            return request.include_rejected
        absolute_delta = abs(float(delta))
        if option_type == "call" and not (float(request.delta_min or 0) <= absolute_delta <= float(request.delta_max or 1)):
            return request.include_rejected
        return True

    def _empty_result(self, request: OptionsScanRequest, warnings: list[str], blockers: list[str]) -> OptionsScanResult:
        """Return an empty structured result."""
        return OptionsScanResult(
            symbols_scanned=len(request.symbols),
            contracts_analyzed=0,
            candidates_found=0,
            rejected_count=0,
            top_candidates=[],
            by_symbol={},
            warnings=warnings,
            blockers=blockers,
        )

    def _serialize_symbol_result(self, result: dict) -> dict:
        """Convert symbol result to JSON-friendly output."""
        return {
            "symbol": result["symbol"],
            "underlying_score": result["underlying_score"],
            "contracts_analyzed": result["contracts_analyzed"],
            "rejected_count": result["rejected_count"],
            "ranked_contracts": [contract.to_dict() for contract in result["ranked_contracts"]],
            "warnings": result["warnings"],
            "blockers": result["blockers"],
        }
