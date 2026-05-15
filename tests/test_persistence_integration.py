"""Persistence integration tests."""

from app.bot.paper_trading_bot import PaperTradingBot
from app.config import Settings
from app.execution.paper_broker import PaperBroker
from app.execution.trade_executor import TradeExecutor
from app.portfolio.paper_account import PaperAccount
from app.risk.risk_manager import RiskDecision
from app.storage.database import init_db, reset_engine_cache
from app.storage.trade_journal import TradeJournal
from tests.test_paper_trading_bot import FakeMarketData, FakeRiskManager, FakeSignal, FakeStrategy


def make_journal(tmp_path) -> TradeJournal:
    """Create initialized test journal."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    init_db(database_url)
    return TradeJournal(database_url)


def test_paper_broker_can_record_orders_and_fills(tmp_path) -> None:
    """PaperBroker journals orders/fills without changing behavior."""
    settings = Settings(_env_file=None, ENABLE_TRADE_JOURNAL=True)
    j = make_journal(tmp_path)
    broker = PaperBroker(account=PaperAccount(), settings=settings, journal=j)
    result = broker.place_market_order("BTC/USD", "buy", 0.1, 10000)
    assert result.accepted is True
    assert j.get_recent_orders()[0]["symbol"] == "BTC/USD"
    assert j.get_recent_fills()[0]["symbol"] == "BTC/USD"


def test_paper_trading_bot_records_scan_results_with_mocks(tmp_path) -> None:
    """PaperTradingBot journals scan artifacts with mocked dependencies."""
    settings = Settings(_env_file=None, ALLOWED_SYMBOLS="BTC/USD", BOT_MIN_SECONDS_BETWEEN_SCANS=0, ENABLE_TRADE_JOURNAL=True)
    j = make_journal(tmp_path)
    broker = PaperBroker(account=PaperAccount(), settings=settings, journal=j)
    executor = TradeExecutor(paper_broker=broker, settings=settings)
    bot = PaperTradingBot(
        market_data_service=FakeMarketData(),  # type: ignore[arg-type]
        strategy=FakeStrategy(FakeSignal()),  # type: ignore[arg-type]
        risk_manager=FakeRiskManager(),  # type: ignore[arg-type]
        trade_executor=executor,
        settings=settings,
        journal=j,
    )
    bot.start(manual_start=True)
    scan = bot.scan_once()
    assert scan["trades_executed"] == 1
    assert j.get_recent_scan_results()[0]["symbol"] == "BTC/USD"
    assert j.get_recent_signals()[0]["symbol"] == "BTC/USD"
    assert j.get_recent_risk_decisions()[0]["approved"] is True


def test_fastapi_journal_routes_exist() -> None:
    """Journal routes are registered."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/journal/init" in paths
    assert "/journal/events" in paths
    assert "/journal/signals" in paths
    assert "/journal/risk-decisions" in paths
    assert "/journal/orders" in paths
    assert "/journal/fills" in paths
    assert "/journal/positions" in paths
    assert "/journal/account-snapshots" in paths
    assert "/journal/scans" in paths
    assert "/journal/errors" in paths


def test_no_api_secrets_are_persisted(tmp_path) -> None:
    """Secret-looking payload keys are scrubbed."""
    j = make_journal(tmp_path)
    j.record_bot_event("secret_test", "scrub", {"api_key": "abc", "nested": {"api_secret": "def", "safe": 1}})
    event = j.get_recent_bot_events()[0]
    assert "api_key" not in event["payload"]
    assert "api_secret" not in event["payload"]["nested"]
    assert event["payload"]["nested"]["safe"] == 1


def test_no_live_trading_or_withdrawal_routes_exist() -> None:
    """No live trading or withdrawal routes exist."""
    from app.main import app

    paths = {route.path.lower() for route in app.routes}
    assert not any(path.startswith("/live") for path in paths)
    assert not any("withdraw" in path for path in paths)
