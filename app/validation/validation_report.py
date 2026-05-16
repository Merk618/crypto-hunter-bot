"""Validation report assembly helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from app.validation.real_data_validation_models import RealDataValidationReport, ValidationCheck


def build_validation_report(checks: list[ValidationCheck]) -> RealDataValidationReport:
    """Build an aggregate validation report from checks."""
    by_name = {check.name: check for check in checks}
    warnings: list[str] = []
    blockers: list[str] = []
    for check in checks:
        warnings.extend(check.warnings)
        blockers.extend(check.blockers)

    safety = by_name.get("safety_audit")
    kraken = by_name.get("kraken_public_data")
    moomoo = by_name.get("moomoo_readonly")
    crypto = by_name.get("crypto_signals")
    stock = by_name.get("stock_hunter")
    options = by_name.get("options_scanner")
    alerts = by_name.get("alerts_reporting")
    operator = by_name.get("operator_layer")
    required_checks = [safety, kraken, crypto, alerts, operator]
    passed = all(check is not None and check.passed for check in required_checks)
    return RealDataValidationReport(
        passed=passed,
        generated_at=datetime.now(timezone.utc).isoformat(),
        safety_audit_passed=bool(safety and safety.passed),
        kraken_public_passed=bool(kraken and kraken.passed),
        moomoo_readonly_passed=bool(moomoo and moomoo.passed),
        crypto_signal_passed=bool(crypto and crypto.passed),
        stock_hunter_passed=bool(stock and stock.passed),
        options_scanner_passed=bool(options and options.passed),
        alerts_reporting_passed=bool(alerts and alerts.passed),
        operator_passed=bool(operator and operator.passed),
        checks=[check.to_dict() for check in checks],
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )
