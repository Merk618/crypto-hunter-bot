"""Trade executor that selects paper or live broker behavior."""

from app.config import BotMode, Settings, get_settings
from app.execution.live_broker import LiveBroker
from app.execution.paper_broker import PaperBroker
from app.exchanges.base import BaseExchange


class TradeExecutor:
    """Route trade requests to paper trading by default."""

    def __init__(self, exchange: BaseExchange, settings: Settings | None = None) -> None:
        """Initialize broker facades for execution."""
        self.settings = settings or get_settings()
        self.paper_broker = PaperBroker()
        self.live_broker = LiveBroker(exchange=exchange, settings=self.settings)

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Place an order through the configured safe execution mode."""
        if self.settings.bot_mode == BotMode.LIVE:
            return self.live_broker.place_order(symbol, side, order_type, quantity, price)
        return self.paper_broker.place_order(symbol, side, order_type, quantity, price)
