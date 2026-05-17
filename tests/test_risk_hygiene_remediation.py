"""Risk hygiene remediation tests."""

from app.risk.risk_record_hygiene import RiskRecordHygiene


def record(**kwargs):
    """Build synthetic risk record."""
    data = {
        "id": 1,
        "symbol": "BTC/USD",
        "side": "buy",
        "approved": False,
        "approved_quantity": None,
        "max_quantity": None,
        "risk_amount": None,
        "estimated_notional": None,
        "blockers": ["signal score below minimum"],
        "reasons": [],
        "warnings": [],
        "source": "crypto_hunter_risk_v1",
    }
    data.update(kwargs)
    return data


def test_hygiene_detects_legacy_rejected_records_with_approval_fields() -> None:
    """Legacy rejected records with approval fields are classified."""
    classification = RiskRecordHygiene().classify_risk_record(record(approved_quantity=1.0, max_quantity=1.0, risk_amount=10.0))

    assert classification["classification"] == "LEGACY_INCONSISTENT_REJECTED_RECORD"


def test_hygiene_classifies_clean_rejected_records() -> None:
    """Clean rejected records classify cleanly."""
    classification = RiskRecordHygiene().classify_risk_record(record())

    assert classification["classification"] == "CLEAN_REJECTED_RECORD"


def test_hygiene_classifies_clean_approved_records() -> None:
    """Clean approved records classify cleanly."""
    classification = RiskRecordHygiene().classify_risk_record(record(approved=True, approved_quantity=1.0, max_quantity=1.0, risk_amount=10.0, blockers=[]))

    assert classification["classification"] == "CLEAN_APPROVED_RECORD"


def test_remediation_preview_is_read_only() -> None:
    """Remediation preview never mutates/deletes."""
    preview = RiskRecordHygiene().preview_remediation_plan(records=[record(approved_quantity=1.0)])

    assert preview["preview_only"] is True
    assert preview["destructive_cleanup_allowed"] is False


def test_recent_cleanliness_fails_with_current_inconsistent_records() -> None:
    """Current inconsistent rejected records fail recent cleanliness."""
    current = record(id=2, source="crypto_hunter_risk_v2", approved_quantity=1.0)
    report = RiskRecordHygiene().validate_recent_records_only_from_records([current])

    assert report["passed"] is False
    assert report["current_inconsistency_count"] == 1


def test_recent_cleanliness_passes_with_clean_rejected_records() -> None:
    """Clean rejected records pass recent cleanliness."""
    report = RiskRecordHygiene().validate_recent_records_only_from_records([record()])

    assert report["passed"] is True

