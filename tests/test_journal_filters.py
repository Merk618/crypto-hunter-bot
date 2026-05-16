"""Journal filter tests."""

from app.journal.journal_filters import dedupe_candidates, filter_production_records, is_test_record, normalize_reasons_warnings_blockers


def test_fake_test_records_are_detected() -> None:
    """Fake/demo/test records are classified as test records."""
    assert is_test_record({"symbol": "BTC/USD", "reasons": ["fake signal"]}) is True
    assert is_test_record({"source": "backtest_signal_v1", "symbol": "BTC/USD"}) is True


def test_production_filters_exclude_fake_demo_mock_records() -> None:
    """Production filters remove fake/demo/mock records."""
    records = [
        {"symbol": "BTC/USD", "score": 90, "reasons": ["valid momentum"]},
        {"symbol": "ETH/USD", "score": 90, "reasons": ["fake signal"]},
        {"symbol": "SOL/USD", "score": 90, "source": "mock_signal"},
    ]

    filtered = filter_production_records(records)

    assert [record["symbol"] for record in filtered] == ["BTC/USD"]


def test_duplicated_candidates_are_deduped() -> None:
    """Duplicate symbols keep highest score."""
    deduped = dedupe_candidates([
        {"asset_class": "crypto", "symbol": "BTC/USD", "score": 80},
        {"asset_class": "crypto", "symbol": "BTC/USD", "score": 90},
    ])

    assert len(deduped) == 1
    assert deduped[0]["score"] == 90


def test_malformed_warnings_blockers_are_normalized() -> None:
    """Malformed persisted list values are cleaned."""
    record = normalize_reasons_warnings_blockers({"warnings": "[", "blockers": "[\"bad\"]", "reasons": "fake signal"})

    assert record["warnings"] == []
    assert record["blockers"] == ["bad"]
    assert record["reasons"] == ["fake signal"]
