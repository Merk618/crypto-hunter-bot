"""Dedicated options scanner tests."""

from app.config import Settings
from app.stock_hunter.options_scanner import OptionsScanner
from app.stock_hunter.options_strategy_models import OptionsScanRequest


class Health:
    """Minimal health object."""

    enabled = True
    import_available = True
    connected = True
    read_only = True

    def to_dict(self) -> dict:
        """Return health dictionary."""
        return {"enabled": True, "connected": True, "read_only": True}


class FakeClient:
    """Read-only fake MooMoo client."""

    def __init__(self, available: bool = True, contracts: list[dict] | None = None) -> None:
        self.available = available
        self.contracts = contracts if contracts is not None else [contract()]

    def is_available(self) -> bool:
        """Return configured availability."""
        return self.available

    def get_health(self) -> Health:
        """Return fake health."""
        return Health()

    def get_quote_snapshot(self, symbol: str) -> dict:
        """Return bullish quote."""
        return {
            "available": True,
            "latest_price": 150,
            "ema_20": 145,
            "ema_50": 135,
            "ema_200": 110,
            "rsi": 55,
            "macd_line": 3,
            "macd_signal": 1,
            "volume": 2_000_000,
            "avg_volume": 1_000_000,
            "momentum_5d": 2,
            "momentum_20d": 8,
            "previous_close": 148,
            "bid": 149.9,
            "ask": 150.1,
        }

    def get_historical_candles(self, symbol: str, timeframe: str, limit: int) -> dict:
        """Return empty but available candles."""
        return {"available": True, "candles": []}

    def get_option_chain(self, symbol: str) -> dict:
        """Return fake option chain."""
        return {"available": True, "contracts": self.contracts}


def contract(**overrides) -> dict:
    """Return a valid option contract."""
    data = {
        "symbol": "AAPL260619C00150000",
        "underlying": "AAPL",
        "expiration": "2026-06-19",
        "strike": 150,
        "option_type": "call",
        "bid": 4.9,
        "ask": 5.1,
        "last": 5,
        "volume": 1200,
        "open_interest": 2500,
        "implied_volatility": 0.35,
        "delta": 0.55,
    }
    data.update(overrides)
    return data


def scanner(client: FakeClient) -> OptionsScanner:
    """Create scanner with fake client."""
    return OptionsScanner(settings=Settings(_env_file=None), moomoo_client=client)


def test_options_scanner_handles_moomoo_disabled_cleanly() -> None:
    """Unavailable MooMoo returns blockers and no candidates."""
    result = scanner(FakeClient(available=False)).scan(OptionsScanRequest(symbols=["AAPL"]))

    assert result.top_candidates == []
    assert result.blockers


def test_options_scanner_handles_no_contracts_cleanly() -> None:
    """No contracts returns a clean empty symbol result."""
    result = scanner(FakeClient(contracts=[])).scan(OptionsScanRequest(symbols=["AAPL"]))

    assert result.contracts_analyzed == 0
    assert result.top_candidates == []
    assert result.by_symbol["AAPL"]["warnings"]


def test_options_scanner_scans_multiple_symbols() -> None:
    """Multiple symbols are scanned."""
    result = scanner(FakeClient()).scan(OptionsScanRequest(symbols=["AAPL", "MSFT"]))

    assert result.symbols_scanned == 2
    assert set(result.by_symbol) == {"AAPL", "MSFT"}


def test_options_scanner_returns_top_n() -> None:
    """Scanner enforces top_n."""
    contracts = [contract(symbol=f"AAPL260619C{i}", volume=1200 + i * 100) for i in range(5)]
    result = scanner(FakeClient(contracts=contracts)).scan(OptionsScanRequest(symbols=["AAPL"], top_n=2))

    assert len(result.top_candidates) == 2


def test_options_scanner_sorts_by_total_score_descending() -> None:
    """Top candidates are sorted by score."""
    contracts = [contract(symbol="LOW", volume=600, open_interest=1200), contract(symbol="HIGH", volume=5000, open_interest=8000)]
    result = scanner(FakeClient(contracts=contracts)).scan(OptionsScanRequest(symbols=["AAPL"], top_n=2))
    scores = [candidate["total_score"] for candidate in result.top_candidates]

    assert scores == sorted(scores, reverse=True)


def test_options_scanner_includes_rejected_only_when_requested() -> None:
    """Rejected contracts are hidden unless requested."""
    contracts = [contract(symbol="GOOD"), contract(symbol="BAD", volume=10)]
    hidden = scanner(FakeClient(contracts=contracts)).scan(OptionsScanRequest(symbols=["AAPL"], include_rejected=False))
    included = scanner(FakeClient(contracts=contracts)).scan(OptionsScanRequest(symbols=["AAPL"], include_rejected=True))

    assert all(candidate["label"] != "REJECTED" for candidate in hidden.top_candidates)
    assert any(candidate["label"] == "REJECTED" for candidate in included.by_symbol["AAPL"]["ranked_contracts"])
