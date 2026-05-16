"""MooMoo read-only market data adapter."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_health import MooMooHealth
from app.connectors.moomoo.moomoo_models import MooMooCandle, MooMooOptionContract, MooMooQuoteSnapshot
from app.connectors.moomoo.moomoo_symbol_mapper import MooMooSymbolMapper


class MooMooMarketData:
    """Read-only adapter for MooMoo quote, candle, market-state, and option data."""

    TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "1d", "1w"}

    def __init__(
        self,
        settings: Settings | None = None,
        health_checker: MooMooHealth | None = None,
        symbol_mapper: MooMooSymbolMapper | None = None,
        provider: Any | None = None,
    ) -> None:
        """Initialize market data adapter with optional mocked provider."""
        self.settings = settings or get_settings()
        self.health_checker = health_checker or MooMooHealth(settings=self.settings)
        self.symbol_mapper = symbol_mapper or MooMooSymbolMapper(self.settings.moomoo_market_region)
        self.provider = provider

    def get_quote_snapshot(self, symbol: str) -> dict:
        """Return normalized read-only quote snapshot."""
        readiness = self._readiness()
        try:
            provider_symbol = self.symbol_mapper.to_provider_symbol(symbol)
            user_symbol = self.symbol_mapper.to_user_symbol(provider_symbol)
        except Exception as exc:
            return self._unavailable_quote(symbol, str(exc))
        if readiness:
            return self._unavailable_quote(user_symbol, readiness, provider_symbol)
        try:
            raw = self._call_provider("get_quote_snapshot", provider_symbol)
            return self._parse_quote(user_symbol, provider_symbol, raw).to_dict()
        except Exception as exc:  # noqa: BLE001
            return self._unavailable_quote(user_symbol, f"MooMoo quote call failed: {exc}", provider_symbol)

    def get_historical_candles(self, symbol: str, timeframe: str = "1d", limit: int | None = None) -> dict:
        """Return normalized historical candles."""
        limit = limit or self.settings.moomoo_candle_limit_default
        if timeframe not in self.TIMEFRAMES:
            return {"available": False, "symbol": symbol, "timeframe": timeframe, "candles": [], "message": f"Unsupported MooMoo timeframe: {timeframe}", "source": "moomoo_readonly_candles"}
        readiness = self._readiness()
        try:
            provider_symbol = self.symbol_mapper.to_provider_symbol(symbol)
            user_symbol = self.symbol_mapper.to_user_symbol(provider_symbol)
        except Exception as exc:
            return {"available": False, "symbol": symbol, "timeframe": timeframe, "candles": [], "message": str(exc), "source": "moomoo_readonly_candles"}
        if readiness:
            return {"available": False, "symbol": user_symbol, "provider_symbol": provider_symbol, "timeframe": timeframe, "candles": [], "message": readiness, "source": "moomoo_readonly_candles"}
        try:
            rows = self._call_provider("get_historical_candles", provider_symbol, timeframe, limit)
            candles = [self._parse_candle(user_symbol, provider_symbol, row).to_dict() for row in list(rows or [])[:limit]]
            return {"available": True, "symbol": user_symbol, "provider_symbol": provider_symbol, "timeframe": timeframe, "candles": candles, "source": "moomoo_readonly_candles"}
        except Exception as exc:  # noqa: BLE001
            return {"available": False, "symbol": user_symbol, "provider_symbol": provider_symbol, "timeframe": timeframe, "candles": [], "message": f"MooMoo candle call failed: {exc}", "source": "moomoo_readonly_candles"}

    def get_market_state(self, symbol: str | None = None) -> dict:
        """Return read-only market state."""
        readiness = self._readiness()
        if readiness:
            return {"available": False, "symbol": symbol, "market_region": self.settings.moomoo_market_region, "message": readiness, "source": "moomoo_readonly_market_state"}
        try:
            provider_symbol = self.symbol_mapper.to_provider_symbol(symbol) if symbol else None
            raw = self._call_provider("get_market_state", provider_symbol)
            return {"available": True, "symbol": symbol, "market_state": raw, "source": "moomoo_readonly_market_state"}
        except Exception as exc:  # noqa: BLE001
            return {"available": False, "symbol": symbol, "market_region": self.settings.moomoo_market_region, "message": f"MooMoo market-state call failed: {exc}", "source": "moomoo_readonly_market_state"}

    def get_option_chain(self, symbol: str) -> dict:
        """Return normalized read-only option chain."""
        readiness = self._readiness()
        try:
            provider_symbol = self.symbol_mapper.to_provider_symbol(symbol)
            user_symbol = self.symbol_mapper.to_user_symbol(provider_symbol)
        except Exception as exc:
            return {"available": False, "symbol": symbol, "contracts": [], "message": str(exc), "source": "moomoo_readonly_option_chain_v1"}
        if readiness:
            return {"available": False, "symbol": user_symbol, "provider_symbol": provider_symbol, "contracts": [], "message": readiness, "source": "moomoo_readonly_option_chain_v1"}
        try:
            rows = self._call_provider("get_option_chain", provider_symbol)
            contracts = [self._parse_option(user_symbol, row).to_dict() for row in rows or []]
            return {"available": True, "symbol": user_symbol, "provider_symbol": provider_symbol, "contracts": contracts, "source": "moomoo_readonly_option_chain_v1"}
        except Exception as exc:  # noqa: BLE001
            return {"available": False, "symbol": user_symbol, "provider_symbol": provider_symbol, "contracts": [], "message": f"MooMoo option-chain call failed: {exc}", "source": "moomoo_readonly_option_chain_v1"}

    def get_supported_timeframes(self) -> list[str]:
        """Return supported timeframe strings."""
        return sorted(self.TIMEFRAMES)

    def _readiness(self) -> str | None:
        """Return unavailable reason, or None when data calls are allowed."""
        health = self.health_checker.check()
        if not health.enabled:
            return "MooMoo connector disabled"
        if not health.import_available:
            return "moomoo-api package is not importable"
        if not health.connected:
            return "OpenD socket is not reachable"
        if not health.read_only or health.trading_enabled or health.paper_trading_enabled or health.unlock_trade_context:
            return "Unsafe MooMoo trading flag detected"
        if self.provider is None:
            return "MooMoo read-only provider is not configured"
        return None

    def _call_provider(self, method: str, *args):
        """Call a mocked/provider method without using trading APIs."""
        fn = getattr(self.provider, method)
        return fn(*args)

    def _parse_quote(self, symbol: str, provider_symbol: str, raw: dict) -> MooMooQuoteSnapshot:
        """Normalize quote data."""
        return MooMooQuoteSnapshot(
            symbol=symbol,
            provider_symbol=provider_symbol,
            available=True,
            message="MooMoo quote available",
            latest_price=self._float(raw, "latest_price", "last_price", "last", "price"),
            open=self._float(raw, "open"),
            high=self._float(raw, "high"),
            low=self._float(raw, "low"),
            previous_close=self._float(raw, "previous_close", "prev_close"),
            volume=self._float(raw, "volume"),
            turnover=self._float(raw, "turnover"),
            bid=self._float(raw, "bid"),
            ask=self._float(raw, "ask"),
            timestamp=str(raw.get("timestamp") or datetime.now(timezone.utc).isoformat()),
        )

    def _parse_candle(self, symbol: str, provider_symbol: str, raw: dict) -> MooMooCandle:
        """Normalize candle row."""
        return MooMooCandle(
            symbol=symbol,
            provider_symbol=provider_symbol,
            timestamp=str(raw.get("timestamp") or raw.get("time") or raw.get("datetime") or ""),
            open=float(raw.get("open", 0) or 0),
            high=float(raw.get("high", 0) or 0),
            low=float(raw.get("low", 0) or 0),
            close=float(raw.get("close", 0) or 0),
            volume=float(raw.get("volume", 0) or 0),
            turnover=self._float(raw, "turnover"),
        )

    def _parse_option(self, underlying: str, raw: dict) -> MooMooOptionContract:
        """Normalize option contract data."""
        bid = self._float(raw, "bid")
        ask = self._float(raw, "ask")
        spread_pct = self._spread_pct(bid, ask)
        volume = self._int(raw, "volume")
        open_interest = self._int(raw, "open_interest", "oi")
        return MooMooOptionContract(
            symbol=str(raw.get("symbol") or raw.get("code") or ""),
            underlying=str(raw.get("underlying") or underlying).upper(),
            expiration=str(raw.get("expiration") or raw.get("expiry") or ""),
            strike=self._float(raw, "strike"),
            option_type=str(raw.get("option_type") or raw.get("type") or "").lower() or None,
            bid=bid,
            ask=ask,
            last=self._float(raw, "last", "last_price"),
            volume=volume,
            open_interest=open_interest,
            implied_volatility=self._float(raw, "implied_volatility", "iv"),
            delta=self._float(raw, "delta"),
            gamma=self._float(raw, "gamma"),
            theta=self._float(raw, "theta"),
            vega=self._float(raw, "vega"),
            spread_pct=spread_pct,
            liquidity_score=self._liquidity_score(volume, open_interest, spread_pct),
        )

    def _unavailable_quote(self, symbol: str, message: str, provider_symbol: str | None = None) -> dict:
        """Return unavailable quote response."""
        return MooMooQuoteSnapshot(symbol=symbol, provider_symbol=provider_symbol, available=False, message=message).to_dict()

    def _float(self, raw: dict, *keys: str) -> float | None:
        """Read optional float from any key."""
        for key in keys:
            value = raw.get(key)
            if value is not None:
                return float(value)
        return None

    def _int(self, raw: dict, *keys: str) -> int | None:
        """Read optional int from any key."""
        value = self._float(raw, *keys)
        return int(value) if value is not None else None

    def _spread_pct(self, bid: float | None, ask: float | None) -> float | None:
        """Calculate spread percentage."""
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            return None
        mid = (bid + ask) / 2
        return ((ask - bid) / mid) * 100 if mid > 0 else None

    def _liquidity_score(self, volume: int | None, open_interest: int | None, spread_pct: float | None) -> float:
        """Calculate simple liquidity score."""
        if spread_pct is None:
            return 0.0
        return round(min((volume or 0) / 500, 5) + min((open_interest or 0) / 1000, 5) + max(0, 5 - spread_pct), 4)
