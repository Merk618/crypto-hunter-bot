"""Trade executor for safe paper trading and live refusal."""

from app.config import BotMode, Settings, get_settings
from app.execution.paper_broker import PaperBroker


class TradeExecutor:
    """Route execution requests to the paper broker or refuse live mode."""

    def __init__(self, paper_broker: PaperBroker | None = None, settings: Settings | None = None) -> None:
        """Initialize the trade executor."""
        self.settings = settings or get_settings()
        self.paper_broker = paper_broker or PaperBroker(settings=self.settings)

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Refuse live mode and route paper market orders for backward compatibility."""
        if self.settings.bot_mode == BotMode.LIVE:
            raise RuntimeError("Live trading is not implemented. TradeExecutor refuses live order execution.")
        return self.paper_broker.place_order(symbol, side, order_type, quantity, price)

    def execute_paper_market_order(self, symbol: str, side: str, quantity: float, market_price: float, reason: str | None = None) -> dict:
        """Execute a paper market order in paper mode only."""
        if self.settings.bot_mode == BotMode.LIVE:
            raise RuntimeError("Live trading is not implemented. Paper executor refuses live mode.")
        return self.paper_broker.place_market_order(symbol, side, quantity, market_price, reason).to_dict()

    def close_paper_position(self, symbol: str, market_price: float, reason: str | None = None) -> dict:
        """Close a paper position in paper mode only."""
        if self.settings.bot_mode == BotMode.LIVE:
            raise RuntimeError("Live trading is not implemented. Paper executor refuses live mode.")
        return self.paper_broker.close_position(symbol, market_price, reason).to_dict()

    def get_paper_account_summary(self) -> dict:
        """Return paper account summary."""
        return self.paper_broker.get_account_summary()
