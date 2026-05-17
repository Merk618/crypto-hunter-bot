"""Phase 29 observation report polish tests."""

from app.observation.observation_report import build_observation_report
from tests.test_early_recovery_watchlist import run


def test_observation_report_includes_early_recovery_candidates() -> None:
    """Observation report includes observe-only early recovery candidates."""
    report = build_observation_report([run(1), run(2), run(3)]).to_dict()

    assert report["early_recovery_candidates"]
    assert report["early_recovery_candidates"][0]["action"] == "OBSERVE_ONLY"


def test_observation_report_includes_window_counts_and_notes() -> None:
    """Observation report includes polished counts and safety notes."""
    report = build_observation_report([run(1), run(2, "refused")]).to_dict()

    assert report["completed_runs_analyzed"] == 1
    assert report["refused_runs_count"] == 1
    assert report["total_attempted_runs"] == 2
    assert any("EMA 200 remains required" in note for note in report["notes"])


def test_observation_report_includes_strongest_and_dominant_blockers() -> None:
    """Observation report exposes strongest symbols and blockers."""
    report = build_observation_report([run(1), run(2), run(3)]).to_dict()

    assert report["strongest_symbols"][0]["symbol"] == "SUI/USD"
    assert report["dominant_blockers"][0]["text"] == "close at or below EMA 200"

