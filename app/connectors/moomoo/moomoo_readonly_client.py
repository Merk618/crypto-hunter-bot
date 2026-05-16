"""Read-only MooMoo feasibility client."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_health import MooMooHealth
from app.connectors.moomoo.moomoo_models import MooMooCapabilityReport, MooMooQuoteSnapshot


class MooMooReadOnlyClient:
    """Safe read-only wrapper for future MooMoo market-data work."""

    def __init__(self, settings: Settings | None = None, health_checker: MooMooHealth | None = None) -> None:
        """Initialize client without opening trade context."""
        self.settings = settings or get_settings()
        self.health_checker = health_checker or MooMooHealth(settings=self.settings)

    def is_available(self) -> bool:
        """Return True only when enabled, importable, and OpenD is connected."""
        health = self.get_health()
        return bool(health.enabled and health.import_available and health.connected and health.read_only)

    def get_health(self):
        """Return MooMoo health status."""
        return self.health_checker.check()

    def get_supported_capabilities(self) -> MooMooCapabilityReport:
        """Return planned read-only capabilities."""
        return MooMooCapabilityReport()

    def get_quote_snapshot(self, symbol: str) -> dict:
        """Return a safe unavailable placeholder until MooMoo data is wired."""
        if not self.is_available():
            return MooMooQuoteSnapshot(symbol=symbol, available=False, message="MooMoo read-only quote data unavailable").to_dict()
        return MooMooQuoteSnapshot(symbol=symbol, available=False, message="MooMoo quote retrieval not implemented in feasibility phase").to_dict()

    def get_historical_candles(self, symbol: str, timeframe: str, limit: int) -> dict:
        """Return a safe historical-candle placeholder."""
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "available": False,
            "candles": [],
            "message": "MooMoo historical candle retrieval is read-only planned work, not implemented in this phase",
            "source": "moomoo_readonly_historical_candles_v1",
        }

    def get_option_chain(self, symbol: str) -> dict:
        """Return a safe option-chain placeholder."""
        return {
            "symbol": symbol,
            "available": False,
            "contracts": [],
            "message": "MooMoo option-chain retrieval is planned for a future read-only phase",
            "source": "moomoo_readonly_option_chain_v1",
        }

    def get_market_state(self) -> dict:
        """Return a safe market-state placeholder."""
        return {
            "available": False,
            "market_region": self.settings.moomoo_market_region,
            "message": "MooMoo market-state retrieval is planned for a future read-only phase",
            "source": "moomoo_readonly_market_state_v1",
        }
