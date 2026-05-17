"""Observation persistence helpers."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.storage.trade_journal import TradeJournal


class ObservationPersistenceService:
    """Persist observation runs and results through the journal."""

    def __init__(self, journal: TradeJournal | None = None, settings: Settings | None = None) -> None:
        """Initialize persistence service."""
        self.settings = settings or get_settings()
        self.journal = journal if journal is not None else TradeJournal()

    def persist_run(self, run: dict) -> dict | None:
        """Persist one observation run and nested results."""
        if not self.settings.observation_persistence_enabled:
            return None
        try:
            self.journal.init()
            return self.journal.record_observation_run_with_results(run)
        except Exception:
            return None

    def persist_result(self, run_id: str, result: dict) -> dict | None:
        """Persist one observation result."""
        if not self.settings.observation_persistence_enabled:
            return None
        try:
            self.journal.init()
            return self.journal.record_observation_result(run_id, result)
        except Exception:
            return None

