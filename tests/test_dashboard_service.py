"""Dashboard service tests."""

from app.bot.bot_state import BotState
from app.execution.paper_broker import PaperBroker
from app.portfolio.paper_account import PaperAccount
from app.reporting.dashboard_service import DashboardService
from app.risk.risk_manager import RiskManager
from app.storage.database import init_db, reset_engine_cache
from app.storage.trade_journal import TradeJournal
from tests.test_trade_journal import sample_fill, sample_order, sample_risk, sample_signal


def make_service(tmp_path) -> tuple[DashboardService, TradeJournal]:
    """Create dashboard service with temp journal."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'reports.db'}"
    init_db(database_url)
    journal = TradeJournal(database_url)
    broker = PaperBroker(account=PaperAccount(), journal=None)
    service = DashboardService(BotState(), broker, RiskManager(), journal)
    return service, journal


def test_dashboard_service_returns_overview_with_empty_journal(tmp_path) -> None:
    """Overview works with empty journal."""
    service, _ = make_service(tmp_path)
    overview = service.get_overview()
    assert overview.mode == "paper"
    assert overview.paper_equity == 10000


def test_dashboard_service_returns_paper_performance_with_default_account(tmp_path) -> None:
    """Paper performance works with default account."""
    service, _ = make_service(tmp_path)
    report = service.get_paper_performance()
    assert report.starting_cash == 10000
    assert report.current_equity == 10000


def test_signal_report_counts_categories_correctly(tmp_path) -> None:
    """Signal report counts categories."""
    service, journal = make_service(tmp_path)
    journal.record_signal(sample_signal("BTC/USD"))
    signal = sample_signal("ETH/USD")
    object.__setattr__(signal, "category", "NEUTRAL")
    object.__setattr__(signal, "score", 50)
    journal.record_signal(signal)
    report = service.get_signal_performance()
    assert report.strong_buy_count == 1
    assert report.neutral_count == 1


def test_signal_report_ranks_symbols_by_latest_score(tmp_path) -> None:
    """Signal report ranks latest score."""
    service, journal = make_service(tmp_path)
    journal.record_signal(sample_signal("BTC/USD"))
    signal = sample_signal("ETH/USD")
    object.__setattr__(signal, "score", 95)
    journal.record_signal(signal)
    assert service.get_signal_performance().symbols_ranked_by_latest_score[0]["symbol"] == "ETH/USD"


def test_risk_summary_includes_kill_switch_status(tmp_path) -> None:
    """Risk summary includes kill switch."""
    service, _ = make_service(tmp_path)
    service.risk_manager.kill_switch.activate("test")
    assert service.get_risk_summary().kill_switch_active is True


def test_recent_activity_returns_events_orders_fills_signals_errors(tmp_path) -> None:
    """Recent activity aggregates journal records."""
    service, journal = make_service(tmp_path)
    journal.record_bot_event("started", "ok")
    journal.record_paper_order(sample_order())
    journal.record_paper_fill(sample_fill())
    journal.record_signal(sample_signal())
    journal.record_error("x", "ValueError", "bad")
    report = service.get_recent_activity()
    assert report.recent_events
    assert report.recent_orders
    assert report.recent_fills
    assert report.recent_signals
    assert report.recent_errors
