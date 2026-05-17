"""Risk record hygiene tests."""

from app.risk.risk_record_hygiene import RiskRecordHygiene


def record(**kwargs):
    """Build risk record."""
    data = {
        "id": 1,
        "symbol": "BTC/USD",
        "side": "buy",
        "approved": False,
        "approved_quantity": None,
        "max_quantity": None,
        "risk_amount": None,
        "blockers": ["signal score below minimum"],
        "reasons": [],
        "warnings": [],
    }
    data.update(kwargs)
    return data


def test_risk_hygiene_detects_rejected_with_approved_quantity() -> None:
    """Rejected record cannot have approved quantity."""
    issues = RiskRecordHygiene().scan_records([record(approved_quantity=1.0)])

    assert any(issue.issue_type == "REJECTED_WITH_APPROVED_QUANTITY" for issue in issues)


def test_risk_hygiene_detects_rejected_with_risk_amount() -> None:
    """Rejected record cannot have risk amount."""
    issues = RiskRecordHygiene().scan_records([record(risk_amount=100.0)])

    assert any(issue.issue_type == "REJECTED_WITH_RISK_AMOUNT" for issue in issues)


def test_risk_hygiene_detects_approved_with_blockers() -> None:
    """Approved record cannot have blockers."""
    issues = RiskRecordHygiene().scan_records([record(approved=True, approved_quantity=1.0, blockers=["bad"])])

    assert any(issue.issue_type == "APPROVED_WITH_BLOCKERS" for issue in issues)


def test_risk_hygiene_clean_report_passes_consistent_rejected_records() -> None:
    """Consistent rejected risk records pass hygiene."""
    summary = RiskRecordHygiene().summary(records=[record()])

    assert summary["passed"] is True
    assert summary["inconsistency_count"] == 0

