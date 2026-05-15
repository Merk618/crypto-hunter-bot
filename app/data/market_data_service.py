"""Market data service wrapping the configured exchange adapter."""

from app.config import ExchangeName, Settings, get_settings
from app.exchanges.base import BaseExchange
from app.exchanges.coinbase_adapter import CoinbaseAdapter
from app.exchanges.kraken_adapter import KrakenAdapter


class MarketDataService:
    """Provide clean public market data for configured symbols."""

    def __init__(self, exchange: BaseExchange | None = None, settings: Settings | None = None) -> None:
        """Initialize the service with an exchange adapter."""
        self.settings = settings or get_settings()
        self.exchange = exchange or self._build_exchange()

    def get_watchlist_tickers(self) -> list[dict]:
        """Return ticker data for every configured allowed symbol."""
        return [self.get_symbol_ticker(symbol) for symbol in self.settings.allowed_symbols]

    def get_symbol_ticker(self, symbol: str) -> dict:
        """Return ticker data for one symbol."""
        return self.exchange.get_ticker(self._safe_path_symbol(symbol))

    def get_symbol_candles(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> list[dict]:
        """Return candle data records for one symbol."""
        df = self.exchange.get_candles(self._safe_path_symbol(symbol), timeframe=timeframe, limit=limit)
        return df.to_dict(orient="records")

    def get_symbols(self) -> list[str]:
        """Return normalized tradable symbols from the exchange."""
        return self.exchange.get_symbols()

    def _build_exchange(self) -> BaseExchange:
        """Create the selected exchange adapter."""
        if self.settings.exchange == ExchangeName.KRAKEN:
            return KrakenAdapter(settings=self.settings)
        return CoinbaseAdapter(settings=self.settings)

    def _safe_path_symbol(self, symbol: str) -> str:
        """Convert FastAPI-safe BTC-USD path symbols into BTC/USD."""
        return symbol.strip().upper().replace("-", "/")
