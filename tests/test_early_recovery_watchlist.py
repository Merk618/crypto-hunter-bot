"""Early recovery watchlist tests."""

from datetime import datetime, timezone

from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.observation.observation_persistence import ObservationPersistenceService
from app.storage.database import init_db, reset_engine_cache
from app.storage.trade_journal import TradeJournal


def result(symbol, score, category="NEUTRAL"):
    """Build synthetic observation result."""
    return {
        "symbol": symbol,
        "timeframe": "1h",
        "action_taken": "observed",
        "signal": {
            "symbol": symbol,
            "score": score,
            "category": category,
            "blockers": ["close at or below EMA 200"],
            "reasons": ["MACD positive momentum"],
            "component_scores": {"momentum": 5},
        },
        "risk_decision": {"approved": False},
        "paper_trade_result": None,
        "reasons": ["MACD positive momentum"],
        "warnings": [],
        "blockers": ["close at or below EMA 200"],
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def run(idx, status="completed"):
    """Build synthetic run."""
    return {
        "run_id": f"run-{idx}-{status}",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "symbols_requested": 2,
        "symbols_processed": 2 if status == "completed" else 0,
        "signals_generated": 2 if status == "completed" else 0,
        "risk_decisions_generated": 2 if status == "completed" else 0,
        "paper_trades_created": 0,
        "warnings": [],
        "blockers": [],
        "results": [result("SUI/USD", 61), result("BTC/USD", 50)] if status == "completed" else [result("SOL/USD", 63)],
    }


def persisted_service(tmp_path):
    """Create persisted watchlist service."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    init_db(database_url)
    journal = TradeJournal(database_url)
    persistence = ObservationPersistenceService(journal)
    return persistence, EarlyRecoveryWatchlistService(hydration=None, runs=None, settings=None), journal


def test_watchlist_builds_from_persisted_completed_observations(tmp_path) -> None:
    """Watchlist uses persisted completed observations."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    init_db(database_url)
    journal = TradeJournal(database_url)
    persistence = ObservationPersistenceService(journal)
    for idx in range(3):
        persistence.persist_run(run(idx))

    service = EarlyRecoveryWatchlistService(hydration=__import__("app.observation.observation_hydration", fromlist=["ObservationHydrationService"]).ObservationHydrationService(journal))
    report = service.get_report()

    assert report["candidates"]
    assert report["candidates"][0]["symbol"] == "SUI/USD"


def test_watchlist_ignores_refused_runs() -> None:
    """Refused runs do not feed candidates."""
    service = EarlyRecoveryWatchlistService(runs=[run(1, "refused")])

    assert service.get_report()["candidates"] == []


def test_sui_like_candidate_ranks_above_lower_score_candidate() -> None:
    """Higher average score ranks first."""
    service = EarlyRecoveryWatchlistService(runs=[run(1), run(2), run(3)])
    candidates = service.get_report()["candidates"]

    assert candidates[0]["symbol"] == "SUI/USD"
    assert candidates[0]["average_score"] > candidates[1]["average_score"]


def test_candidate_is_observe_only_and_trade_flags_false() -> None:
    """Candidate cannot trade."""
    item = EarlyRecoveryWatchlistService(runs=[run(1), run(2), run(3)]).get_report()["candidates"][0]

    assert item["action"] == "OBSERVE_ONLY"
    assert item["trade_allowed"] is False
    assert item["paper_trade_allowed"] is False
    assert item["live_trade_allowed"] is False


def test_candidate_includes_ema_blocker_and_momentum() -> None:
    """Candidate explains blocker and momentum evidence."""
    item = EarlyRecoveryWatchlistService(runs=[run(1), run(2), run(3)]).get_report()["candidates"][0]

    assert "close at or below EMA 200" in item["dominant_blockers"]
    assert item["momentum_evidence"]


def test_empty_history_returns_empty_watchlist() -> None:
    """Empty history is clean."""
    report = EarlyRecoveryWatchlistService(runs=[]).get_report()

    assert report["candidates"] == []

