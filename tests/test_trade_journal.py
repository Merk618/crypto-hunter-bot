"""Trade journal tests."""

from datetime import datetime, timezone
from types import SimpleNamespace

from pydantic import BaseModel

from app.bot.scan_result import ScanResult
from app.models.trading_models import PaperFill, PaperOrder, PaperPosition
from app.risk.risk_manager import RiskDecision
from app.storage.database import init_db, reset_engine_cache
from app.storage.serializers import to_plain_data
from app.storage.trade_journal import TradeJournal
from app.strategies.signal_scoring import SignalResult


def journal(tmp_path) -> TradeJournal:
    """Create a temp journal."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    init_db(database_url)
    return TradeJournal(database_url)


def sample_signal(symbol: str = "BTC/USD") -> SignalResult:
    """Build sample signal."""
    return SignalResult(
        symbol=symbol,
        timeframe="1h",
        timestamp=datetime.now(timezone.utc),
        score=84,
        category="STRONG_BUY",
        risk_level="LOW",
        reasons=["trend"],
        warnings=[],
        blockers=[],
        component_scores={"trend": 25, "raw_score": 84},
        latest_price=100.0,
        suggested_entry=100.0,
        suggested_stop_loss=90.0,
        suggested_take_profit=130.0,
        atr=10.0,
        exit_watch=False,
        trim_zone=False,
        momentum_warning=None,
    )


def sample_risk(symbol: str = "BTC/USD") -> RiskDecision:
    """Build sample risk decision."""
    return RiskDecision(
        approved=True,
        symbol=symbol,
        side="buy",
        requested_quantity=None,
        approved_quantity=1.0,
        max_quantity=1.0,
        reasons=["ok"],
        warnings=[],
        blockers=[],
        risk_amount=100.0,
        estimated_notional=100.0,
    )


def sample_order() -> PaperOrder:
    """Build sample order."""
    now = datetime.now(timezone.utc)
    return PaperOrder("order-1", "BTC/USD", "buy", "market", 1.0, 100.0, 100.1, "filled", now, now, "test")


def sample_fill() -> PaperFill:
    """Build sample fill."""
    return PaperFill("fill-1", "order-1", "BTC/USD", "buy", 1.0, 100.1, 0.25, 0.1, datetime.now(timezone.utc))


def sample_position() -> PaperPosition:
    """Build sample position."""
    now = datetime.now(timezone.utc)
    return PaperPosition("BTC/USD", 1.0, 100.0, 110.0, 110.0, 10.0, 0.0, now, now)


def test_trade_journal_records_and_reads_bot_events(tmp_path) -> None:
    """Bot events round-trip."""
    j = journal(tmp_path)
    j.record_bot_event("started", "Bot started", {"safe": True})
    rows = j.get_recent_bot_events()
    assert rows[0]["event_type"] == "started"
    assert rows[0]["payload"]["safe"] is True


def test_trade_journal_records_and_reads_signal_records(tmp_path) -> None:
    """Signal records round-trip."""
    j = journal(tmp_path)
    j.record_signal(sample_signal())
    rows = j.get_recent_signals()
    assert rows[0]["symbol"] == "BTC/USD"
    assert rows[0]["component_scores"]["raw_score"] == 84


def test_trade_journal_records_and_reads_risk_decisions(tmp_path) -> None:
    """Risk decisions round-trip."""
    j = journal(tmp_path)
    j.record_risk_decision(sample_risk())
    rows = j.get_recent_risk_decisions()
    assert rows[0]["approved"] is True
    assert rows[0]["reasons"] == ["ok"]


def test_trade_journal_records_and_reads_paper_orders(tmp_path) -> None:
    """Paper orders round-trip."""
    j = journal(tmp_path)
    j.record_paper_order(sample_order())
    rows = j.get_recent_orders()
    assert rows[0]["order_id"] == "order-1"


def test_trade_journal_records_and_reads_paper_fills(tmp_path) -> None:
    """Paper fills round-trip."""
    j = journal(tmp_path)
    j.record_paper_fill(sample_fill())
    rows = j.get_recent_fills()
    assert rows[0]["fill_id"] == "fill-1"


def test_trade_journal_records_and_reads_paper_positions(tmp_path) -> None:
    """Paper positions round-trip."""
    j = journal(tmp_path)
    j.record_paper_position(sample_position())
    rows = j.get_recent_positions("BTC/USD")
    assert rows[0]["symbol"] == "BTC/USD"


def test_trade_journal_records_account_snapshots(tmp_path) -> None:
    """Account snapshots round-trip."""
    j = journal(tmp_path)
    j.record_account_snapshot({"cash_balance": 1000, "equity": 1100, "realized_pnl": 10, "unrealized_pnl": 90, "total_fees_paid": 1, "open_positions": 1})
    rows = j.get_recent_account_snapshots()
    assert rows[0]["equity"] == 1100


def test_trade_journal_records_scan_results(tmp_path) -> None:
    """Scan results round-trip."""
    j = journal(tmp_path)
    scan = ScanResult("BTC/USD", signal=sample_signal(), risk_decision=sample_risk(), action_taken="paper_buy", reasons=["ok"])
    j.record_scan_result(scan)
    rows = j.get_recent_scan_results()
    assert rows[0]["action_taken"] == "paper_buy"
    assert rows[0]["signal"]["symbol"] == "BTC/USD"


def test_trade_journal_records_errors(tmp_path) -> None:
    """Errors round-trip."""
    j = journal(tmp_path)
    j.record_error("bot", "ValueError", "bad", {"x": 1})
    rows = j.get_recent_errors()
    assert rows[0]["component"] == "bot"
    assert rows[0]["payload"]["x"] == 1


def test_recent_read_methods_respect_limit(tmp_path) -> None:
    """Recent readers apply limits."""
    j = journal(tmp_path)
    for idx in range(3):
        j.record_bot_event("event", str(idx))
    assert len(j.get_recent_bot_events(limit=2)) == 2


def test_symbol_filters_work(tmp_path) -> None:
    """Symbol filters narrow results."""
    j = journal(tmp_path)
    j.record_signal(sample_signal("BTC/USD"))
    j.record_signal(sample_signal("ETH/USD"))
    rows = j.get_recent_signals(symbol="ETH/USD")
    assert len(rows) == 1
    assert rows[0]["symbol"] == "ETH/USD"


class PydanticThing(BaseModel):
    """Pydantic-style test object."""

    symbol: str
    api_secret: str


def test_serializers_handle_dataclasses_dicts_and_pydantic_objects() -> None:
    """Serializer supports supported object styles and scrubs secrets."""
    assert to_plain_data(sample_order())["order_id"] == "order-1"
    assert to_plain_data({"api_key": "secret", "safe": True}) == {"safe": True}
    assert to_plain_data(PydanticThing(symbol="BTC/USD", api_secret="secret")) == {"symbol": "BTC/USD"}
    assert to_plain_data(SimpleNamespace(x=1)) == "namespace(x=1)"
