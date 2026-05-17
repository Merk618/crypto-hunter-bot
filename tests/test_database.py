"""Database initialization tests."""

from sqlalchemy import inspect

from app.storage.database import get_engine, init_db, reset_engine_cache


def test_init_db_creates_tables(tmp_path) -> None:
    """init_db creates all journal tables."""
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    reset_engine_cache()
    init_db(database_url)
    tables = set(inspect(get_engine(database_url)).get_table_names())
    assert {
        "bot_events",
        "signal_records",
        "risk_decisions",
        "paper_orders",
        "paper_fills",
        "paper_positions",
        "account_snapshots",
        "scan_results",
        "error_records",
        "observation_runs",
        "observation_results",
    }.issubset(tables)
