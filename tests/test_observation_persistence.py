"""Observation persistence tests."""

from datetime import datetime, timezone

from app.config import Settings
from app.observation.observation_persistence import ObservationPersistenceService
from app.storage.database import init_db, reset_engine_cache
from app.storage.trade_journal import TradeJournal


def make_journal(tmp_path) -> TradeJournal:
    """Create initialized temp journal."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    init_db(database_url)
    return TradeJournal(database_url)


def sample_result(symbol="BTC/USD") -> dict:
    """Build sample observation result."""
    return {
        "symbol": symbol,
        "timeframe": "1h",
        "signal": {"symbol": symbol, "score": 61, "category": "NEUTRAL", "blockers": ["close at or below EMA 200"]},
        "risk_decision": {"approved": False},
        "paper_trade_result": None,
        "action_taken": "observed",
        "reasons": ["MACD positive momentum"],
        "warnings": [],
        "blockers": ["close at or below EMA 200"],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": "crypto_hunter_observation_result_v1",
    }


def sample_run(status="completed") -> dict:
    """Build sample observation run."""
    return {
        "run_id": f"run-{status}",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "symbols_requested": 1,
        "symbols_processed": 1 if status == "completed" else 0,
        "signals_generated": 1 if status == "completed" else 0,
        "risk_decisions_generated": 1 if status == "completed" else 0,
        "paper_trades_created": 0,
        "warnings": [],
        "blockers": [],
        "results": [sample_result()] if status == "completed" else [],
        "source": "crypto_hunter_observation_run_v1",
    }


def test_completed_observation_run_is_persisted(tmp_path) -> None:
    """Completed observation run persists."""
    journal = make_journal(tmp_path)
    ObservationPersistenceService(journal, Settings()).persist_run(sample_run())

    rows = journal.get_recent_observation_runs(completed_only=True)

    assert rows[0]["run_id"] == "run-completed"
    assert rows[0]["status"] == "completed"


def test_observation_results_are_persisted(tmp_path) -> None:
    """Observation results persist."""
    journal = make_journal(tmp_path)
    ObservationPersistenceService(journal, Settings()).persist_run(sample_run())

    rows = journal.get_recent_observation_results()

    assert rows[0]["symbol"] == "BTC/USD"
    assert rows[0]["signal"]["score"] == 61


def test_refused_run_can_persist_but_not_count_completed(tmp_path) -> None:
    """Refused run persists but completed reader ignores it."""
    journal = make_journal(tmp_path)
    ObservationPersistenceService(journal, Settings()).persist_run(sample_run("refused"))

    assert journal.get_recent_observation_runs(completed_only=False)[0]["status"] == "refused"
    assert journal.get_recent_observation_runs(completed_only=True) == []

