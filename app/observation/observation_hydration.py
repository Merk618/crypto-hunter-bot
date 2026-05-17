"""Hydrate observation history from persisted storage."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.storage.trade_journal import TradeJournal


class ObservationHydrationService:
    """Load persisted observation history for reports and decision gates."""

    def __init__(self, journal: TradeJournal | None = None, settings: Settings | None = None) -> None:
        """Initialize hydration service."""
        self.settings = settings or get_settings()
        self.journal = journal if journal is not None else TradeJournal()

    def load_recent_runs(self, limit: int | None = None, include_refused: bool = False) -> list[dict]:
        """Load recent runs and attach their results."""
        if not self.settings.observation_hydration_enabled:
            return []
        limit = limit or self.settings.observation_history_limit
        try:
            self.journal.init()
            rows = self.journal.get_recent_observation_runs(limit=limit, completed_only=(self.settings.observation_require_completed_runs_only and not include_refused))
            return [self._attach_results(row) for row in rows if include_refused or row.get("status") == "completed"]
        except Exception:
            return []

    def load_recent_results(self, limit: int | None = None, include_refused: bool = False) -> list[dict]:
        """Load recent observation results."""
        runs = self.load_recent_runs(limit=limit, include_refused=include_refused)
        return [result for run in runs for result in run.get("results", [])]

    def history_summary(self, limit: int | None = None) -> dict:
        """Return persisted observation history summary."""
        completed = self.load_recent_runs(limit=limit, include_refused=False)
        all_runs = self.load_recent_runs(limit=limit, include_refused=True)
        return {
            "completed_runs": len(completed),
            "refused_runs": sum(1 for run in all_runs if run.get("status") == "refused"),
            "total_runs": len(all_runs),
            "results": sum(len(run.get("results", [])) for run in completed),
            "source": "crypto_hunter_observation_hydration_summary_v1",
        }

    def _attach_results(self, run: dict) -> dict:
        """Attach persisted results to one run record."""
        results = self.journal.get_recent_observation_results(limit=self.settings.observation_history_limit, run_id=run.get("run_id"))
        hydrated = dict(run)
        hydrated["results"] = list(reversed(results))
        return hydrated

