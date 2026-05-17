"""Observation hydration tests."""

from app.config import Settings
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_persistence import ObservationPersistenceService
from app.storage.database import init_db, reset_engine_cache
from app.storage.trade_journal import TradeJournal
from tests.test_observation_persistence import sample_run


def make_services(tmp_path):
    """Create persistence and hydration services."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    init_db(database_url)
    journal = TradeJournal(database_url)
    settings = Settings(DATABASE_URL=database_url)
    return ObservationPersistenceService(journal, settings), ObservationHydrationService(journal, settings)


def test_hydration_loads_completed_runs_after_restart(tmp_path) -> None:
    """Hydration reconstructs completed runs."""
    persistence, _ = make_services(tmp_path)
    persistence.persist_run(sample_run())
    _, hydration = make_services(tmp_path)

    runs = hydration.load_recent_runs()

    assert runs[0]["status"] == "completed"
    assert runs[0]["results"][0]["symbol"] == "BTC/USD"


def test_hydration_ignores_refused_runs_by_default(tmp_path) -> None:
    """Hydration ignores refused runs by default."""
    persistence, hydration = make_services(tmp_path)
    persistence.persist_run(sample_run("refused"))

    assert hydration.load_recent_runs() == []
    assert hydration.load_recent_runs(include_refused=True)[0]["status"] == "refused"

