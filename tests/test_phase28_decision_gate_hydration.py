"""Phase 28 decision gate hydration tests."""

from datetime import datetime, timezone

from app.calibration.strategy_calibration_report import StrategyCalibrationReportBuilder
from app.calibration.strategy_decision_gate import StrategyDecisionGate
from app.observation.early_recovery import EarlyRecoveryClassifier
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_persistence import ObservationPersistenceService
from app.storage.database import init_db, reset_engine_cache
from app.storage.trade_journal import TradeJournal


def make_hydration(tmp_path):
    """Create temp persistence/hydration pair."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    init_db(database_url)
    journal = TradeJournal(database_url)
    return ObservationPersistenceService(journal), ObservationHydrationService(journal)


def result(symbol, score, category):
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


def run(idx):
    """Build current observed pattern run."""
    return {
        "run_id": f"run-{idx}",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "symbols_requested": 4,
        "symbols_processed": 4,
        "signals_generated": 4,
        "risk_decisions_generated": 4,
        "paper_trades_created": 0,
        "warnings": [],
        "blockers": [],
        "results": [
            result("SUI/USD", 61, "NEUTRAL"),
            result("ETH/USD", 54, "NEUTRAL"),
            result("BTC/USD", 44, "WEAK"),
            result("SOL/USD", 40, "WEAK"),
        ],
    }


def test_calibration_report_can_use_persisted_observations(tmp_path) -> None:
    """Calibration report works from hydrated observations."""
    persistence, hydration = make_hydration(tmp_path)
    persistence.persist_run(run(1))

    report = StrategyCalibrationReportBuilder().build(hydration.load_recent_runs())

    assert report["observations_analyzed"] == 4
    assert report["category_distribution"]["NEUTRAL"] == 2


def test_decision_gate_can_use_persisted_observations(tmp_path) -> None:
    """Decision gate works from hydrated observations."""
    persistence, hydration = make_hydration(tmp_path)
    for idx in range(5):
        persistence.persist_run(run(idx))

    report = StrategyDecisionGate().evaluate(hydration.load_recent_runs()).to_dict()

    assert report["decision"] == "ADD_EARLY_RECOVERY_WATCHLIST"
    assert report["live_review_allowed"] is False
    assert report["paper_trade_observation_allowed"] is False


def test_early_recovery_can_use_persisted_observations(tmp_path) -> None:
    """Early recovery candidates work from hydrated observations."""
    persistence, hydration = make_hydration(tmp_path)
    for idx in range(3):
        persistence.persist_run(run(idx))

    candidates = EarlyRecoveryClassifier().classify_runs(hydration.load_recent_runs())

    assert candidates[0].symbol == "SUI/USD"

