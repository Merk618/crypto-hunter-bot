"""Reporting performance summary tests."""

from app.reporting.performance_summary import calculate_return_pct, rank_symbols_by_latest_signal, summarize_signals


def test_performance_summary_calculates_returns_correctly() -> None:
    """Return percentage is calculated."""
    assert calculate_return_pct(100, 125) == 25


def test_performance_summary_handles_zero_starting_equity_safely() -> None:
    """Zero starting equity returns 0."""
    assert calculate_return_pct(0, 125) == 0


def test_signal_summary_and_rankings() -> None:
    """Signal summaries count and rank categories."""
    signals = [
        {"symbol": "BTC/USD", "score": 80, "category": "STRONG_BUY", "created_at": "1"},
        {"symbol": "ETH/USD", "score": 60, "category": "NEUTRAL", "created_at": "2"},
        {"symbol": "BTC/USD", "score": 90, "category": "STRONG_BUY", "created_at": "3"},
    ]
    summary = summarize_signals(signals)
    ranked = rank_symbols_by_latest_signal(signals)
    assert summary["strong_buy_count"] == 2
    assert summary["neutral_count"] == 1
    assert ranked[0]["symbol"] == "BTC/USD"
