"""Paper trading bot tests."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from app.bot.bot_state import BotState
from app.bot.paper_trading_bot import PaperTradingBot, PaperTradingBotError
from app.config import Settings
from app.execution.paper_broker import PaperBroker
from app.execution.trade_executor import TradeExecutor
from app.portfolio.paper_account import PaperAccount
from app.risk.risk_manager import RiskDecision


class Clock:
    """Mutable test clock."""

    def __init__(self) -> None:
        """Initialize clock."""
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def advance(self, seconds: int) -> None:
        """Advance clock."""
        self.now += timedelta(seconds=seconds)


class FakeMarketData:
    """Fake market data service."""

    def get_symbol_candles(self, symbol: str, timeframe: str = "1h", limit: int = 250) -> list[dict]:
        """Return fake candles."""
        return [{"symbol": symbol, "close": 100.0, "timestamp": pd.Timestamp("2026-01-01T00:00:00Z")}]


class FakeSignal:
    """Fake signal result."""

    def __init__(self, score: int = 84, category: str = "STRONG_BUY") -> None:
        """Initialize fake signal."""
        self.symbol = "BTC/USD"
        self.timeframe = "1h"
        self.timestamp = "2026-01-01T00:00:00Z"
        self.score = score
        self.category = category
        self.blockers = []
        self.reasons = ["fake signal"]
        self.warnings = []
        self.latest_price = 100.0
        self.suggested_stop_loss = 90.0

    def to_dict(self) -> dict:
        """Return dict output."""
        return self.__dict__.copy()


class FakeStrategy:
    """Fake strategy."""

    def __init__(self, signal: FakeSignal | None = None) -> None:
        """Initialize fake strategy."""
        self.signal = signal or FakeSignal()

    def evaluate(self, candles, symbol: str, timeframe: str = "1h") -> FakeSignal:
        """Return fake signal."""
        self.signal.symbol = symbol
        return self.signal


class FakeRiskManager:
    """Fake risk manager."""

    def __init__(self, approved: bool = True, approved_quantity: float | None = 1.0) -> None:
        """Initialize fake risk manager."""
        self.approved = approved
        self.approved_quantity = approved_quantity
        self.calls = 0

    def evaluate_trade(self, **kwargs) -> RiskDecision:
        """Return fake risk decision."""
        self.calls += 1
        blockers = [] if self.approved else ["risk rejected"]
        return RiskDecision(
            approved=self.approved,
            symbol=kwargs["symbol"],
            side=kwargs["side"],
            requested_quantity=None,
            approved_quantity=self.approved_quantity,
            max_quantity=self.approved_quantity,
            reasons=["risk ok"] if self.approved else [],
            warnings=[],
            blockers=blockers,
            risk_amount=100.0,
            estimated_notional=(self.approved_quantity or 0) * kwargs["market_price"] if self.approved else None,
        )


def make_bot(settings: Settings | None = None, signal: FakeSignal | None = None, risk: FakeRiskManager | None = None, clock: Clock | None = None) -> PaperTradingBot:
    """Create a paper trading bot with fakes."""
    settings = settings or Settings(_env_file=None, BOT_MIN_SECONDS_BETWEEN_SCANS=60, ALLOWED_SYMBOLS="BTC/USD")
    paper_broker = PaperBroker(account=PaperAccount(), settings=settings)
    executor = TradeExecutor(paper_broker=paper_broker, settings=settings)
    clock = clock or Clock()
    return PaperTradingBot(
        market_data_service=FakeMarketData(),  # type: ignore[arg-type]
        strategy=FakeStrategy(signal),  # type: ignore[arg-type]
        risk_manager=risk or FakeRiskManager(),  # type: ignore[arg-type]
        trade_executor=executor,
        state=BotState(),
        settings=settings,
        now_fn=lambda: clock.now,
    )


def test_start_refuses_when_auto_disabled_without_manual_start() -> None:
    """start refuses when auto trading is disabled unless manual_start is passed."""
    bot = make_bot()
    with pytest.raises(PaperTradingBotError):
        bot.start()


def test_start_manual_starts_in_paper_mode() -> None:
    """manual_start starts paper bot."""
    bot = make_bot()
    status = bot.start(manual_start=True)
    assert status["is_running"] is True


def test_stop_pause_resume() -> None:
    """Bot supports stop, pause, and resume."""
    bot = make_bot()
    bot.start(manual_start=True)
    assert bot.pause()["is_paused"] is True
    assert bot.resume()["is_paused"] is False
    assert bot.stop()["is_running"] is False


def test_scan_once_refuses_if_bot_is_stopped() -> None:
    """scan_once requires running bot."""
    with pytest.raises(PaperTradingBotError):
        make_bot().scan_once()


def test_scan_once_respects_minimum_scan_interval() -> None:
    """scan_once enforces minimum interval."""
    clock = Clock()
    bot = make_bot(clock=clock)
    bot.start(manual_start=True)
    bot.scan_once()
    with pytest.raises(PaperTradingBotError):
        bot.scan_once()


def test_scan_symbol_generates_signal_and_risk_decision() -> None:
    """scan_symbol returns signal and risk decision."""
    bot = make_bot()
    result = bot.scan_symbol("BTC/USD")
    assert result.signal is not None
    assert result.risk_decision is not None


def test_approved_strong_buy_places_paper_buy() -> None:
    """Approved STRONG_BUY executes paper buy."""
    bot = make_bot()
    bot.start(manual_start=True)
    result = bot.scan_once()
    assert result["trades_executed"] == 1


def test_low_score_signal_does_not_place_trade() -> None:
    """Low score signal does not buy."""
    bot = make_bot(signal=FakeSignal(score=60, category="NEUTRAL"))
    bot.start(manual_start=True)
    result = bot.scan_once()
    assert result["trades_executed"] == 0


def test_risk_rejection_does_not_place_trade() -> None:
    """Risk rejection prevents buy."""
    bot = make_bot(risk=FakeRiskManager(approved=False))
    bot.start(manual_start=True)
    result = bot.scan_once()
    assert result["trades_executed"] == 0


def test_duplicate_symbol_is_not_traded_twice_in_same_scan() -> None:
    """Duplicate configured symbols do not produce duplicate trades."""
    settings = Settings(_env_file=None, ALLOWED_SYMBOLS="BTC/USD,BTC/USD", BOT_MIN_SECONDS_BETWEEN_SCANS=60)
    bot = make_bot(settings=settings)
    bot.start(manual_start=True)
    result = bot.scan_once()
    assert result["trades_executed"] == 1
    assert result["symbols_scanned"] == 2


def test_missing_approved_quantity_does_not_place_trade() -> None:
    """Missing approved quantity prevents buy."""
    bot = make_bot(risk=FakeRiskManager(approved=True, approved_quantity=None))
    bot.start(manual_start=True)
    result = bot.scan_once()
    assert result["trades_executed"] == 0


def test_paper_allow_autobuy_false_prevents_buy() -> None:
    """Config can disable paper autobuy."""
    settings = Settings(_env_file=None, PAPER_ALLOW_AUTOBUY=False, ALLOWED_SYMBOLS="BTC/USD")
    bot = make_bot(settings=settings)
    bot.start(manual_start=True)
    result = bot.scan_once()
    assert result["trades_executed"] == 0


def test_live_mode_is_refused() -> None:
    """Live mode cannot start the paper bot."""
    settings = Settings(_env_file=None, BOT_MODE="live")
    bot = make_bot(settings=settings)
    with pytest.raises(PaperTradingBotError):
        bot.start(manual_start=True)


def test_fastapi_bot_routes_exist() -> None:
    """Bot routes are registered."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/bot/status" in paths
    assert "/bot/start" in paths
    assert "/bot/stop" in paths
    assert "/bot/pause" in paths
    assert "/bot/resume" in paths
    assert "/bot/scan-once" in paths


def test_no_live_trading_or_withdrawal_routes_exist() -> None:
    """No live trading or withdrawal routes exist."""
    from app.main import app

    paths = {route.path.lower() for route in app.routes}
    assert not any(path.startswith("/live") for path in paths)
    assert not any("withdraw" in path for path in paths)
