"""Live broker safety gate."""

from app.config import Settings, get_settings
from app.exchanges.base import BaseExchange


class LiveTradingDisabledError(RuntimeError):
    """Raised when live trading safety requirements are not satisfied."""


class LiveBroker:
    """Broker facade that refuses live orders unless every safety lock is opened."""

    def __init__(self, exchange: BaseExchange, settings: Settings | None = None) -> None:
        """Initialize with an exchange adapter and settings."""
        self.exchange = exchange
        self.settings = settings or get_settings()

    def _assert_live_trading_allowed(self) -> None:
        """Raise unless all live-trading safety checks pass."""
        if not self.settings.live_trading_allowed():
            raise LiveTradingDisabledError(
                "Live trading is locked. Required: BOT_MODE=live, ENABLE_LIVE_TRADING=true, "
                "REQUIRE_LIVE_CONFIRMATION=false, and exchange API keys configured."
            )

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Place a live order only after passing safety checks."""
        self._assert_live_trading_allowed()
        return self.exchange.place_order(symbol, side, order_type, quantity, price)
