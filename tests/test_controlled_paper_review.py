"""Controlled paper review tests."""

from app.observation.controlled_paper_review import ControlledPaperReviewService


def run(**kwargs):
    """Build controlled paper run."""
    data = {
        "run_id": "run-1",
        "status": "PREVIEW_ONLY",
        "completed_at": "2026-05-17T00:00:00+00:00",
        "symbols_processed": 1,
        "signals_generated": 1,
        "risk_decisions_generated": 1,
        "paper_trade_previews_created": 1,
        "paper_trades_created": 0,
        "blocked_trades": 1,
        "warnings": [],
        "blockers": [],
        "trade_results": [],
    }
    data.update(kwargs)
    return data


def test_review_returns_clean_empty_report() -> None:
    """Empty review is clean and warns no runs exist."""
    report = ControlledPaperReviewService().review([])

    assert report["recent_runs_count"] == 0
    assert report["paper_trades_created"] == 0
    assert report["warnings"]


def test_review_counts_preview_only_separately() -> None:
    """Preview-only records are counted separately from paper trades."""
    report = ControlledPaperReviewService().review([run()])

    assert report["recent_previews_count"] == 1
    assert report["preview_only_count"] == 1
    assert report["paper_trades_created"] == 0


def test_review_detects_paper_trades_created_count() -> None:
    """Paper trades are counted when present."""
    report = ControlledPaperReviewService().review([run(paper_trades_created=1, trade_results=[{"mode": "CONTROLLED_PAPER_OBSERVATION", "broker": "PAPER", "real_execution": False, "live_trade": False}])])

    assert report["paper_trades_created"] == 1
    assert report["paper_only_labels_valid"] is True


def test_review_invalid_labels_create_blocker() -> None:
    """Invalid controlled labels are reported."""
    report = ControlledPaperReviewService().review([run(paper_trades_created=1, trade_results=[{"mode": "WRONG", "broker": "PAPER", "real_execution": False, "live_trade": False}])])

    assert report["paper_only_labels_valid"] is False
    assert report["blockers"]
