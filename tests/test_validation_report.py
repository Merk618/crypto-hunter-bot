"""Validation report tests."""

from app.validation.real_data_validation_models import ValidationCheck
from app.validation.validation_report import build_validation_report


def test_validation_report_builds_structured_output() -> None:
    """Aggregate report has expected source and flags."""
    report = build_validation_report([
        ValidationCheck("safety_audit", True, "passed", "ok"),
        ValidationCheck("kraken_public_data", False, "failed", "down", blockers=["network unavailable"]),
        ValidationCheck("crypto_signals", False, "failed", "no signal"),
        ValidationCheck("alerts_reporting", True, "passed", "ok"),
        ValidationCheck("operator_layer", True, "passed", "ok"),
    ])

    data = report.to_dict()
    assert data["source"] == "crypto_hunter_real_data_validation_v1"
    assert data["passed"] is False
    assert "network unavailable" in data["blockers"]
