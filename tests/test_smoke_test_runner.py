"""Phase 14 smoke-test runner tests."""

from dataclasses import dataclass

from app.config import Settings
from app.diagnostics.smoke_test_runner import SmokeTestRunner


@dataclass
class FakeAuditReport:
    """Minimal audit report for smoke tests."""

    passed: bool = True
    live_trading_locked: bool = True
    blockers: list[str] = None

    def __post_init__(self) -> None:
        """Initialize mutable fields."""
        if self.blockers is None:
            self.blockers = []

    def to_dict(self) -> dict:
        """Return report dict."""
        return {"passed": self.passed, "live_trading_locked": self.live_trading_locked, "blockers": self.blockers}


class FakeAudit:
    """Fake safety audit."""

    def __init__(self, report: FakeAuditReport | None = None) -> None:
        self.report = report or FakeAuditReport()

    def run(self) -> FakeAuditReport:
        """Return fake report."""
        return self.report


class FakeMarketData:
    """Fake public market data."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def get_symbol_ticker(self, symbol: str) -> dict:
        """Return a fake ticker."""
        if self.fail:
            raise RuntimeError("market data unavailable")
        return {"symbol": symbol, "bid": 99, "ask": 101, "last": 100}

    def get_symbol_candles(self, symbol: str, timeframe: str, limit: int):
        """Return fake candles."""
        if self.fail:
            raise RuntimeError("candles unavailable")
        return [{"timestamp": "2026-01-01T00:00:00Z", "open": 99, "high": 101, "low": 98, "close": 100, "volume": 10}]


class FakeSignal:
    """Fake signal result."""

    symbol = "BTC/USD"
    timeframe = "1h"
    latest_price = 100.0
    category = "STRONG_BUY"
    score = 84

    def to_dict(self) -> dict:
        """Return signal dict."""
        return {"symbol": self.symbol, "timeframe": self.timeframe, "latest_price": self.latest_price, "category": self.category, "score": self.score, "blockers": []}


class FakeStrategy:
    """Fake strategy."""

    def evaluate(self, candles, symbol: str, timeframe: str) -> FakeSignal:
        """Return fake signal."""
        signal = FakeSignal()
        signal.symbol = symbol
        signal.timeframe = timeframe
        return signal


class FakeRiskDecision:
    """Fake risk decision."""

    approved = False

    def to_dict(self) -> dict:
        """Return risk dict."""
        return {"approved": self.approved, "blockers": ["synthetic no trade"]}


class FakeRiskManager:
    """Fake risk manager."""

    def evaluate_trade(self, *args, **kwargs) -> FakeRiskDecision:
        """Return fake risk decision."""
        return FakeRiskDecision()


class FakePaperBot:
    """Fake paper bot."""

    def start(self, manual_start: bool = False) -> dict:
        """Return paper start status."""
        return {"is_running": True, "mode": "paper", "manual_start": manual_start}

    def scan_once(self) -> dict:
        """Return no-trade scan."""
        return {"scan_results": [], "trades_executed": 0, "symbols_scanned": 0}


class FakeJournal:
    """Fake journal."""

    def __init__(self) -> None:
        self.events = []

    def record_bot_event(self, event_type: str, message: str, payload=None) -> None:
        """Record event."""
        self.events.append({"event_type": event_type, "message": message, "payload": payload})

    def get_recent_bot_events(self, limit: int = 5) -> list[dict]:
        """Return events."""
        return self.events[-limit:]


class FakeDashboard:
    """Fake dashboard."""

    def get_full_dashboard_snapshot(self) -> dict:
        """Return fake dashboard."""
        return {"overview": {}, "paper_performance": {}}


def runner(**overrides) -> SmokeTestRunner:
    """Build a smoke runner with fake dependencies."""
    values = {
        "settings": Settings(_env_file=None, PHASE14_SMOKE_SYMBOLS="BTC/USD"),
        "market_data_service": FakeMarketData(),
        "strategy": FakeStrategy(),
        "risk_manager": FakeRiskManager(),
        "paper_bot": FakePaperBot(),
        "journal": FakeJournal(),
        "dashboard_service": FakeDashboard(),
        "safety_audit": FakeAudit(),
    }
    values.update(overrides)
    return SmokeTestRunner(**values)


def test_smoke_runner_returns_pass_fail_checks() -> None:
    """Smoke runner returns structured check output."""
    result = runner().run()

    assert result["source"] == "crypto_hunter_phase14_smoke_test"
    assert isinstance(result["checks"], list)
    assert result["live_trading_locked"] is True


def test_smoke_runner_confirms_live_trading_locked() -> None:
    """Smoke runner reports live trading lock."""
    result = runner().run()

    assert result["live_trading_locked"] is True
    assert result["safety_audit_passed"] is True


def test_smoke_runner_handles_market_data_failure_cleanly() -> None:
    """Market failures are warnings instead of crashes."""
    result = runner(market_data_service=FakeMarketData(fail=True)).run()

    assert result["signals_generated"] == 0
    assert result["warnings"]
    assert any(check["name"] == "market_signal_BTC/USD" and check["passed"] is False for check in result["checks"])


def test_smoke_runner_handles_unavailable_symbol_cleanly() -> None:
    """Unavailable symbols are captured per-symbol."""
    result = runner(settings=Settings(_env_file=None, PHASE14_SMOKE_SYMBOLS="NOPE/USD"), market_data_service=FakeMarketData(fail=True)).run()

    assert result["symbols_checked"] == []
    assert "NOPE/USD" in result["warnings"][0]
