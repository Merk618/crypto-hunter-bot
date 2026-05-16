"""Paper observation engine tests."""

from dataclasses import dataclass

from app.config import Settings
from app.observation.paper_observation_engine import PaperObservationEngine
from app.risk.risk_manager import RiskDecision


@dataclass
class Signal:
    """Fake signal."""

    symbol: str = "BTC/USD"
    timeframe: str = "1h"
    score: int = 90
    category: str = "STRONG_BUY"
    latest_price: float = 100.0
    suggested_stop_loss: float = 95.0
    reasons: list[str] = None
    warnings: list[str] = None
    blockers: list[str] = None
    source: str = "crypto_hunter_signal_v1"

    def __post_init__(self):
        self.reasons = self.reasons or ["valid momentum"]
        self.warnings = self.warnings or []
        self.blockers = self.blockers or []

    def to_dict(self):
        return self.__dict__


class Market:
    """Fake market data."""

    def __init__(self, fail_symbol: str | None = None):
        self.fail_symbol = fail_symbol

    def get_symbol_candles(self, symbol, timeframe, limit):
        if symbol == self.fail_symbol:
            raise RuntimeError("symbol failed")
        return [{"timestamp": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 1.5, "volume": 100} for _ in range(250)]


class Strategy:
    """Fake strategy."""

    def evaluate(self, candles, symbol, timeframe="1h"):
        return Signal(symbol=symbol, timeframe=timeframe)


class Risk:
    """Fake risk manager."""

    def __init__(self, approved=True):
        self.approved = approved

    def evaluate_trade(self, *args, **kwargs):
        return RiskDecision(self.approved, args[0], "buy", None, 1.0 if self.approved else None, 1.0, ["risk ok"] if self.approved else [], [], [] if self.approved else ["risk rejected"], 10.0, 100.0)


class Executor:
    """Fake trade executor."""

    def __init__(self):
        self.live_called = False
        self.paper_broker = self
        self.paper_orders = 0

    def get_paper_account_summary(self):
        return {"equity": 10000, "cash_balance": 10000, "realized_pnl": 0}

    def get_positions(self):
        return []

    def execute_paper_market_order(self, *args, **kwargs):
        self.paper_orders += 1
        return {"accepted": True, "message": "paper only"}


class Readiness:
    """Fake readiness."""

    def __init__(self):
        self.checked = False

    def check(self):
        self.checked = True
        return {"ready": True, "warnings": [], "blockers": []}


class Journal:
    """Fake journal."""

    def __init__(self):
        self.signals = 0
        self.risks = 0

    def record_signal(self, signal):
        self.signals += 1

    def record_risk_decision(self, risk):
        self.risks += 1


def engine(settings=None, **overrides):
    defaults = {
        "settings": settings or Settings(_env_file=None),
        "market_data_service": Market(),
        "strategy": Strategy(),
        "risk_manager": Risk(),
        "trade_executor": Executor(),
        "readiness_checker": Readiness(),
        "journal": Journal(),
    }
    defaults.update(overrides)
    return PaperObservationEngine(**defaults)


def test_observation_engine_refuses_when_disabled_and_not_manual() -> None:
    """Disabled observation refuses automatic run."""
    result = engine().run_once(manual_run=False)

    assert result["status"] == "refused"


def test_observation_engine_allows_manual_run() -> None:
    """Manual run bypasses disabled default."""
    result = engine().run_once(manual_run=True)

    assert result["status"] == "completed"
    assert result["signals_generated"] > 0


def test_observation_readiness_is_checked() -> None:
    """Readiness checker is called."""
    readiness = Readiness()
    engine(readiness_checker=readiness).run_once(manual_run=True)

    assert readiness.checked is True


def test_observe_symbol_generates_signal_and_risk_decision() -> None:
    """One symbol observation generates signal and risk."""
    result = engine().observe_symbol("BTC/USD")

    assert result.signal is not None
    assert result.risk_decision is not None


def test_signal_and_risk_decision_are_journaled() -> None:
    """Observation journals signal and risk."""
    journal = Journal()
    engine(journal=journal).observe_symbol("BTC/USD")

    assert journal.signals == 1
    assert journal.risks == 1


def test_no_paper_trade_when_observation_paper_trades_disabled() -> None:
    """Paper trades are disabled by default."""
    executor = Executor()
    result = engine(trade_executor=executor).observe_symbol("BTC/USD", allow_paper_trades=True)

    assert result.paper_trade_result is None
    assert executor.paper_orders == 0


def test_paper_trade_created_only_when_enabled_and_risk_approved() -> None:
    """Paper trade can occur only under explicit paper settings."""
    settings = Settings(_env_file=None, PAPER_OBSERVATION_ALLOW_PAPER_TRADES=True)
    executor = Executor()
    result = engine(settings=settings, trade_executor=executor).observe_symbol("BTC/USD", allow_paper_trades=True)

    assert result.paper_trade_result is not None
    assert executor.paper_orders == 1


def test_live_broker_is_never_called() -> None:
    """Engine only uses paper executor method."""
    executor = Executor()
    engine(settings=Settings(_env_file=None, PAPER_OBSERVATION_ALLOW_PAPER_TRADES=True), trade_executor=executor).observe_symbol("BTC/USD", allow_paper_trades=True)

    assert executor.live_called is False


def test_per_symbol_failure_does_not_crash_whole_run() -> None:
    """One symbol failure becomes a result blocker."""
    settings = Settings(_env_file=None, PAPER_OBSERVATION_SYMBOLS=["BTC/USD", "ETH/USD"])
    result = engine(settings=settings, market_data_service=Market(fail_symbol="ETH/USD")).run_once(manual_run=True)

    assert result["status"] == "completed"
    assert result["symbols_processed"] == 2
    assert result["blockers"]


def test_minimum_seconds_between_runs_enforced() -> None:
    """Back-to-back runs are throttled."""
    obs = engine()
    obs.run_once(manual_run=True)
    second = obs.run_once(manual_run=True)

    assert second["status"] == "refused"
