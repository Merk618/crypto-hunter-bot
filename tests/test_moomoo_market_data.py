"""MooMoo read-only market data tests."""

from app.config import Settings
from app.connectors.moomoo.moomoo_health import MooMooHealth
from app.connectors.moomoo.moomoo_market_data import MooMooMarketData


class FakeProvider:
    """Mock MooMoo provider."""

    def get_quote_snapshot(self, provider_symbol: str) -> dict:
        """Return fake quote."""
        return {
            "latest_price": 200,
            "open": 190,
            "high": 205,
            "low": 188,
            "previous_close": 189,
            "volume": 1000000,
            "turnover": 200000000,
            "bid": 199.9,
            "ask": 200.1,
            "timestamp": "2026-01-01T15:00:00Z",
        }

    def get_historical_candles(self, provider_symbol: str, timeframe: str, limit: int) -> list[dict]:
        """Return fake candles."""
        return [{"timestamp": "2026-01-01", "open": 190, "high": 205, "low": 188, "close": 200, "volume": 1000, "turnover": 200000}]

    def get_option_chain(self, provider_symbol: str) -> list[dict]:
        """Return fake options."""
        return [
            {
                "symbol": "US.AAPL260116C00200000",
                "underlying": "AAPL",
                "expiration": "2026-01-16",
                "strike": 200,
                "option_type": "call",
                "bid": 4.9,
                "ask": 5.1,
                "last": 5,
                "volume": 1000,
                "open_interest": 2000,
                "delta": 0.55,
            }
        ]

    def get_market_state(self, provider_symbol=None) -> dict:
        """Return fake state."""
        return {"state": "OPEN", "symbol": provider_symbol}


def health(settings: Settings, import_available: bool = True, connected: bool = True) -> MooMooHealth:
    """Create deterministic health checker."""
    return MooMooHealth(settings, import_checker=lambda _: import_available, socket_checker=lambda host, port: connected)


def market_data(settings: Settings | None = None, import_available: bool = True, connected: bool = True, provider=None) -> MooMooMarketData:
    """Create market data adapter."""
    settings = settings or Settings(_env_file=None, MOOMOO_ENABLED=True)
    return MooMooMarketData(settings=settings, health_checker=health(settings, import_available, connected), provider=provider)


def test_market_data_returns_disabled_response_when_moomoo_disabled() -> None:
    """Disabled MooMoo returns unavailable response."""
    md = market_data(Settings(_env_file=None), provider=FakeProvider())
    quote = md.get_quote_snapshot("AAPL")

    assert quote["available"] is False
    assert "disabled" in quote["message"]


def test_market_data_handles_missing_moomoo_api() -> None:
    """Missing package is a clean unavailable response."""
    quote = market_data(import_available=False, provider=FakeProvider()).get_quote_snapshot("AAPL")

    assert quote["available"] is False
    assert "not importable" in quote["message"]


def test_market_data_handles_disconnected_opend() -> None:
    """Disconnected OpenD is a clean unavailable response."""
    quote = market_data(connected=False, provider=FakeProvider()).get_quote_snapshot("AAPL")

    assert quote["available"] is False
    assert "OpenD socket" in quote["message"]


def test_quote_snapshot_parsing_from_mocked_response() -> None:
    """Quote response is normalized."""
    quote = market_data(provider=FakeProvider()).get_quote_snapshot("AAPL")

    assert quote["available"] is True
    assert quote["symbol"] == "AAPL"
    assert quote["provider_symbol"] == "US.AAPL"
    assert quote["latest_price"] == 200
    assert quote["source"] == "moomoo_readonly_quote"


def test_historical_candle_parsing_from_mocked_response() -> None:
    """Candle response is normalized."""
    candles = market_data(provider=FakeProvider()).get_historical_candles("AAPL", "1d", 250)

    assert candles["available"] is True
    assert candles["candles"][0]["close"] == 200
    assert candles["candles"][0]["provider_symbol"] == "US.AAPL"


def test_option_chain_parsing_from_mocked_response() -> None:
    """Option chain response is normalized."""
    chain = market_data(provider=FakeProvider()).get_option_chain("AAPL")

    assert chain["available"] is True
    assert chain["contracts"][0]["symbol"] == "US.AAPL260116C00200000"
    assert chain["contracts"][0]["spread_pct"] is not None


def test_missing_greeks_are_handled_cleanly() -> None:
    """Unavailable greeks remain None."""
    contract = market_data(provider=FakeProvider()).get_option_chain("AAPL")["contracts"][0]

    assert contract["gamma"] is None
    assert contract["theta"] is None
    assert contract["vega"] is None


def test_supported_timeframes() -> None:
    """Supported timeframes are exposed."""
    assert "1d" in market_data(provider=FakeProvider()).get_supported_timeframes()
