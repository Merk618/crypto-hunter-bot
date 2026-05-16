"""Read-only MooMoo feasibility client."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_health import MooMooHealth
from app.connectors.moomoo.moomoo_market_data import MooMooMarketData
from app.connectors.moomoo.moomoo_models import MooMooCapabilityReport


class MooMooReadOnlyClient:
    """Safe read-only wrapper for future MooMoo market-data work."""

    def __init__(self, settings: Settings | None = None, health_checker: MooMooHealth | None = None, market_data: MooMooMarketData | None = None) -> None:
        """Initialize client without opening trade context."""
        self.settings = settings or get_settings()
        self.health_checker = health_checker or MooMooHealth(settings=self.settings)
        self.market_data = market_data or MooMooMarketData(settings=self.settings, health_checker=self.health_checker)

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
        """Return a read-only quote snapshot."""
        return self.market_data.get_quote_snapshot(symbol)

    def get_historical_candles(self, symbol: str, timeframe: str, limit: int) -> dict:
        """Return read-only historical candles."""
        return self.market_data.get_historical_candles(symbol, timeframe, limit)

    def get_option_chain(self, symbol: str) -> dict:
        """Return read-only option-chain data."""
        return self.market_data.get_option_chain(symbol)

    def get_market_state(self) -> dict:
        """Return read-only market state."""
        return self.market_data.get_market_state()
