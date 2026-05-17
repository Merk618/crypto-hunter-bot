"""Risk decision persistence hygiene tests."""

from app.risk.risk_manager import RiskDecision
from app.storage.database import init_db, reset_engine_cache
from app.storage.serializers import normalize_rejected_risk_payload
from app.storage.trade_journal import TradeJournal


def journal(tmp_path) -> TradeJournal:
    """Create temp journal."""
    reset_engine_cache()
    database_url = f"sqlite:///{tmp_path / 'journal.db'}"
    init_db(database_url)
    return TradeJournal(database_url)


def rejected_decision() -> RiskDecision:
    """Build rejected risk decision with stale approval fields."""
    return RiskDecision(
        approved=False,
        symbol="BTC/USD",
        side="buy",
        requested_quantity=None,
        approved_quantity=1.0,
        max_quantity=1.0,
        reasons=[],
        warnings=[],
        blockers=["blocked"],
        risk_amount=100.0,
        estimated_notional=1000.0,
    )


def approved_decision() -> RiskDecision:
    """Build approved risk decision."""
    return RiskDecision(
        approved=True,
        symbol="BTC/USD",
        side="buy",
        requested_quantity=None,
        approved_quantity=1.0,
        max_quantity=1.0,
        reasons=["ok"],
        warnings=[],
        blockers=[],
        risk_amount=100.0,
        estimated_notional=1000.0,
    )


def test_rejected_risk_decision_normalizes_approved_quantity_to_null() -> None:
    """Rejected payload clears approved quantity."""
    payload = normalize_rejected_risk_payload(rejected_decision().to_dict())

    assert payload["approved_quantity"] is None


def test_rejected_risk_decision_normalizes_max_quantity_to_null() -> None:
    """Rejected payload clears max quantity."""
    payload = normalize_rejected_risk_payload(rejected_decision().to_dict())

    assert payload["max_quantity"] is None


def test_rejected_risk_decision_normalizes_risk_amount_to_null() -> None:
    """Rejected payload clears risk amount and estimated notional."""
    payload = normalize_rejected_risk_payload(rejected_decision().to_dict())

    assert payload["risk_amount"] is None
    assert payload["estimated_notional"] is None


def test_approved_risk_decision_preserves_approval_fields() -> None:
    """Approved payload keeps approval fields."""
    payload = normalize_rejected_risk_payload(approved_decision().to_dict())

    assert payload["approved_quantity"] == 1.0
    assert payload["max_quantity"] == 1.0
    assert payload["risk_amount"] == 100.0


def test_journal_normalizes_rejected_payload_before_persistence(tmp_path) -> None:
    """Journal write path normalizes rejected risk decisions."""
    j = journal(tmp_path)
    j.record_risk_decision(rejected_decision())
    row = j.get_recent_risk_decisions()[0]

    assert row["approved"] is False
    assert row["approved_quantity"] is None
    assert row["max_quantity"] is None
    assert row["risk_amount"] is None

