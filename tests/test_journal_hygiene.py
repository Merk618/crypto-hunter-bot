"""Journal hygiene tests."""

from app.journal.journal_hygiene import JournalHygiene


class FakeJournal:
    """Fake journal records."""

    def get_recent_signals(self, limit=500):
        return [
            {"symbol": "BTC/USD", "score": 90, "reasons": ["valid momentum"]},
            {"symbol": "ETH/USD", "score": 90, "reasons": ["fake signal"]},
        ]


def test_journal_hygiene_detects_test_records() -> None:
    """Fake records are detected."""
    records = JournalHygiene(FakeJournal()).detect_test_records()

    assert len(records) == 1
    assert records[0]["symbol"] == "ETH/USD"


def test_journal_hygiene_summarizes_test_records() -> None:
    """Summary is preview-only."""
    summary = JournalHygiene(FakeJournal()).summarize_test_records()

    assert summary["test_records_detected"] == 1
    assert summary["preview_only"] is True


def test_journal_hygiene_filters_production_records() -> None:
    """Production preview excludes fake records."""
    preview = JournalHygiene(FakeJournal()).production_preview()

    assert len(preview["records"]) == 1
    assert preview["records"][0]["symbol"] == "BTC/USD"
