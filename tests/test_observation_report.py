"""Observation report tests."""

from app.observation.observation_report import build_observation_report


def test_observation_report_summarizes_signal_counts() -> None:
    """Report counts signal categories."""
    report = build_observation_report([
        {"results": [{"symbol": "BTC/USD", "signal": {"category": "STRONG_BUY", "score": 90}}]},
        {"results": [{"symbol": "ETH/USD", "signal": {"category": "WEAK", "score": 30}}]},
    ]).to_dict()

    assert report["signal_counts"]["STRONG_BUY"] == 1
    assert report["signal_counts"]["WEAK"] == 1


def test_observation_report_lists_top_signals() -> None:
    """Top signals are sorted by score."""
    report = build_observation_report([
        {"results": [{"symbol": "BTC/USD", "signal": {"category": "BUY", "score": 70}}, {"symbol": "ETH/USD", "signal": {"category": "BUY", "score": 90}}]}
    ]).to_dict()

    assert report["top_signals"][0]["symbol"] == "ETH/USD"
