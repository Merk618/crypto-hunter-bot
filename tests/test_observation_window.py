"""Observation window summary tests."""

from app.config import Settings
from app.observation.observation_window import build_observation_window_summary


def run(category="NEUTRAL", score=54, blocker="close at or below EMA 200"):
    """Build synthetic run."""
    return {"paper_trades_created": 0, "results": [{"symbol": "BTC/USD", "signal": {"category": category, "score": score, "blockers": [blocker]}, "blockers": [blocker]}]}


def test_observation_window_summary_aggregates_categories() -> None:
    """Window summary aggregates categories."""
    summary = build_observation_window_summary("session", [run("NEUTRAL"), run("WEAK")]).to_dict()

    assert summary["category_distribution"]["NEUTRAL"] == 1
    assert summary["category_distribution"]["WEAK"] == 1


def test_observation_window_summary_aggregates_blockers() -> None:
    """Window summary aggregates blockers."""
    summary = build_observation_window_summary("session", [run(), run()]).to_dict()

    assert summary["blocker_distribution"]["close at or below EMA 200"] == 2


def test_observation_window_summary_calibration_readiness() -> None:
    """Window summary reports calibration readiness."""
    settings = Settings(OBSERVATION_WINDOW_MIN_RUNS_FOR_SUMMARY=2)
    summary = build_observation_window_summary("session", [run(), run()], settings=settings).to_dict()

    assert summary["calibration_readiness"] == "PARTIAL"
