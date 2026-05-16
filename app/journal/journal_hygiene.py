"""Preview-first journal hygiene tools."""

from __future__ import annotations

from collections import Counter

from app.journal.journal_filters import dedupe_candidates, filter_production_records, is_test_record, label_record_type, normalize_reasons_warnings_blockers
from app.storage.trade_journal import TradeJournal


class JournalHygiene:
    """Read-only hygiene helper for persisted journal data."""

    def __init__(self, trade_journal: TradeJournal | None = None) -> None:
        """Initialize hygiene helper."""
        self.trade_journal = trade_journal or TradeJournal()

    def detect_test_records(self, limit: int = 500) -> list[dict]:
        """Return journal signal records that look fake/demo/test."""
        records = self._recent_records(limit)
        return [normalize_reasons_warnings_blockers(record) for record in records if is_test_record(record)]

    def detect_test_records_from(self, records: list[dict]) -> list[dict]:
        """Detect test records from supplied records."""
        return [normalize_reasons_warnings_blockers(record) for record in records if is_test_record(record)]

    def summarize_test_records(self, limit: int = 500) -> dict:
        """Summarize test/demo records without deleting anything."""
        records = self._recent_records(limit)
        types = Counter(label_record_type(record) for record in records)
        test_records = [record for record in records if is_test_record(record)]
        return {
            "total_records_reviewed": len(records),
            "test_records_detected": len(test_records),
            "record_types": dict(types),
            "preview_only": True,
            "source": "crypto_hunter_journal_hygiene_summary_v1",
        }

    def filter_production_records(self, limit: int = 500) -> list[dict]:
        """Return production-style journal records."""
        return filter_production_records(self._recent_records(limit))

    def production_preview(self, limit: int = 500) -> dict:
        """Return production preview with deduped candidates."""
        production = self.filter_production_records(limit)
        return {
            "records": production,
            "deduped_candidates": dedupe_candidates(production),
            "preview_only": True,
            "source": "crypto_hunter_journal_production_preview_v1",
        }

    def normalize_reasons_warnings_blockers(self, record: dict) -> dict:
        """Expose normalization helper."""
        return normalize_reasons_warnings_blockers(record)

    def dedupe_candidates(self, candidates: list[dict]) -> list[dict]:
        """Expose candidate dedupe helper."""
        return dedupe_candidates(candidates)

    def _recent_records(self, limit: int) -> list[dict]:
        """Read recent signal records."""
        try:
            return self.trade_journal.get_recent_signals(limit=limit)
        except Exception:
            return []
