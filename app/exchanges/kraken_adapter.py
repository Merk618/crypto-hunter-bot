"""Kraken public market data adapter."""

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from app.config import Settings, get_settings
from app.exchanges.base import BaseExchange


class KrakenAdapterError(RuntimeError):
    """Base exception for Kraken adapter failures."""


class KrakenRequestError(KrakenAdapterError):
    """Raised when a Kraken public REST request fails."""


class InvalidSymbolError(KrakenAdapterError):
    """Raised when a requested symbol is unavailable."""


class UnsupportedTimeframeError(KrakenAdapterError):
    """Raised when a requested timeframe is unsupported."""


class EmptyMarketDataError(KrakenAdapterError):
    """Raised when Kraken returns no usable market data."""


class KrakenAdapter(BaseExchange):
    """Kraken adapter for public market data only."""

    BASE_URL = "https://api.kraken.com/0/public"
    TIMEFRAME_TO_INTERVAL = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "1d": 1440,
    }
    ASSET_ALIASES = {
        "XBT": "BTC",
        "XXBT": "BTC",
        "XETH": "ETH",
        "ZUSD": "USD",
        "ZUSDT": "USDT",
        "ZEUR": "EUR",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the Kraken adapter."""
        self.settings = settings or get_settings()
        self._symbol_to_exchange: dict[str, str] = {}
        self._exchange_to_symbol: dict[str, str] = {}

    def get_symbols(self) -> list[str]:
        """Fetch tradable asset pairs and return normalized symbols."""
        self._ensure_symbol_map()
        return sorted(self._symbol_to_exchange)

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> Any:
        """Fetch Kraken OHLC candles as a clean DataFrame."""
        exchange_symbol = self.to_exchange_symbol(symbol)
        interval = self.timeframe_to_interval(timeframe)
        payload = self._public_request("OHLC", {"pair": exchange_symbol, "interval": interval})
        result = payload.get("result", {})
        rows = result.get(exchange_symbol) or self._first_market_result(result)
        if not rows:
            raise EmptyMarketDataError(f"No OHLC data returned for {symbol}")

        normalized_symbol = self.normalize_symbol(symbol)
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "vwap", "volume", "count"])
        numeric_float_cols = ["open", "high", "low", "close", "vwap", "volume"]
        for column in numeric_float_cols:
            df[column] = pd.to_numeric(df[column], errors="raise").astype(float)
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"], errors="raise"), unit="s", utc=True)
        df["count"] = pd.to_numeric(df["count"], errors="raise").astype(int)
        df["symbol"] = normalized_symbol
        df["exchange_symbol"] = exchange_symbol
        df = df.sort_values("timestamp", ascending=True).tail(max(1, int(limit))).reset_index(drop=True)
        return df[
            [
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "vwap",
                "volume",
                "count",
                "symbol",
                "exchange_symbol",
            ]
        ]

    def get_ticker(self, symbol: str) -> dict:
        """Fetch and parse Kraken ticker data."""
        exchange_symbol = self.to_exchange_symbol(symbol)
        payload = self._public_request("Ticker", {"pair": exchange_symbol})
        result = payload.get("result", {})
        ticker = result.get(exchange_symbol) or self._first_market_result(result)
        if not ticker:
            raise EmptyMarketDataError(f"No ticker data returned for {symbol}")
        return {
            "symbol": self.normalize_symbol(symbol),
            "exchange_symbol": exchange_symbol,
            "bid": float(ticker["b"][0]),
            "ask": float(ticker["a"][0]),
            "last": float(ticker["c"][0]),
            "volume": float(ticker["v"][1]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "kraken",
        }

    def get_orderbook(self, symbol: str) -> dict:
        """Fetch Kraken public order book data."""
        exchange_symbol = self.to_exchange_symbol(symbol)
        payload = self._public_request("Depth", {"pair": exchange_symbol})
        result = payload.get("result", {})
        book = result.get(exchange_symbol) or self._first_market_result(result)
        if not book:
            raise EmptyMarketDataError(f"No orderbook data returned for {symbol}")
        return {
            "symbol": self.normalize_symbol(symbol),
            "exchange_symbol": exchange_symbol,
            "bids": [[float(price), float(volume), int(timestamp)] for price, volume, timestamp in book.get("bids", [])],
            "asks": [[float(price), float(volume), int(timestamp)] for price, volume, timestamp in book.get("asks", [])],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_balance(self) -> dict:
        """Return empty balance data without exposing credentials."""
        return {}

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None) -> dict:
        """Refuse live orders because Kraken execution is not implemented in Phase 1."""
        raise NotImplementedError("Kraken live order placement is not implemented in Phase 1")

    def cancel_order(self, order_id: str) -> dict:
        """Refuse cancellation because live order management is not implemented in Phase 1."""
        raise NotImplementedError("Kraken live order cancellation is not implemented in Phase 1")

    def get_open_orders(self) -> list[dict]:
        """Return no open live orders in Phase 1."""
        return []

    def get_positions(self) -> list[dict]:
        """Return no live positions in Phase 1."""
        return []

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbols to human-readable slash pairs."""
        cleaned = symbol.strip().upper().replace("-", "/")
        if "/" not in cleaned and cleaned.endswith(self.settings.base_currency):
            base = cleaned[: -len(self.settings.base_currency)]
            cleaned = f"{base}/{self.settings.base_currency}"
        parts = cleaned.split("/")
        if len(parts) != 2 or not all(parts):
            raise InvalidSymbolError(f"Invalid symbol format: {symbol}")
        base, quote = parts
        return f"{self._normalize_asset(base)}/{self._normalize_asset(quote)}"

    def timeframe_to_interval(self, timeframe: str) -> int:
        """Convert bot timeframe strings to Kraken interval minutes."""
        try:
            return self.TIMEFRAME_TO_INTERVAL[timeframe]
        except KeyError as exc:
            raise UnsupportedTimeframeError(f"Unsupported timeframe: {timeframe}") from exc

    def to_exchange_symbol(self, symbol: str) -> str:
        """Resolve a normalized symbol into Kraken's native pair key."""
        normalized = self.normalize_symbol(symbol)
        self._ensure_symbol_map()
        exchange_symbol = self._symbol_to_exchange.get(normalized)
        if not exchange_symbol:
            raise InvalidSymbolError(f"Symbol is not available on Kraken: {normalized}")
        return exchange_symbol

    def _ensure_symbol_map(self) -> None:
        """Load and cache Kraken pair mappings."""
        if self._symbol_to_exchange:
            return
        payload = self._public_request("AssetPairs")
        result = payload.get("result", {})
        if not result:
            raise EmptyMarketDataError("Kraken AssetPairs returned no tradable pairs")
        for exchange_symbol, pair_info in result.items():
            if pair_info.get("status") and pair_info["status"] != "online":
                continue
            normalized = self._normalized_symbol_from_pair(pair_info)
            if not normalized:
                continue
            self._symbol_to_exchange.setdefault(normalized, exchange_symbol)
            self._exchange_to_symbol[exchange_symbol] = normalized

    def _normalized_symbol_from_pair(self, pair_info: dict) -> str | None:
        """Create a human-readable symbol from Kraken pair metadata."""
        wsname = pair_info.get("wsname")
        if wsname and "/" in wsname:
            base, quote = wsname.split("/", maxsplit=1)
            return f"{self._normalize_asset(base)}/{self._normalize_asset(quote)}"

        base = pair_info.get("base")
        quote = pair_info.get("quote")
        if not base or not quote:
            return None
        return f"{self._normalize_asset(base)}/{self._normalize_asset(quote)}"

    def _normalize_asset(self, asset: str) -> str:
        """Normalize Kraken asset codes to common names."""
        cleaned = asset.strip().upper()
        if cleaned in self.ASSET_ALIASES:
            return self.ASSET_ALIASES[cleaned]
        if len(cleaned) > 3 and cleaned[0] in {"X", "Z"}:
            stripped = cleaned[1:]
            return self.ASSET_ALIASES.get(stripped, stripped)
        return cleaned

    def _public_request(self, endpoint: str, params: dict | None = None) -> dict:
        """Call a Kraken public REST endpoint and return decoded JSON."""
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.BASE_URL}/{endpoint}{query}"
        try:
            with urlopen(url, timeout=10) as response:
                data = response.read()
        except Exception as exc:  # noqa: BLE001 - urllib can raise several exception types
            raise KrakenRequestError(f"Kraken public request failed for {endpoint}") from exc

        try:
            import json

            payload = json.loads(data.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise KrakenRequestError(f"Kraken returned invalid JSON for {endpoint}") from exc

        errors = payload.get("error") or []
        if errors:
            raise KrakenRequestError(f"Kraken returned error for {endpoint}: {', '.join(errors)}")
        return payload

    def _first_market_result(self, result: dict) -> Any:
        """Return the first market payload value, ignoring Kraken metadata keys."""
        for key, value in result.items():
            if key != "last":
                return value
        return None
