"""Validate Kraken public data and crypto signals without API keys."""

from __future__ import annotations

import json
import sys

from app.validation.real_data_validator import RealDataValidator
from app.validation.validation_report import build_validation_report


def main() -> int:
    """Print Kraken validation report."""
    validator = RealDataValidator()
    report = build_validation_report([
        validator.validate_safety_audit(),
        validator.validate_kraken_public_data(),
        validator.validate_crypto_signals(),
    ]).to_dict()
    print(json.dumps(report, indent=2))
    return 0 if report.get("kraken_public_passed") and report.get("crypto_signal_passed") else 1


if __name__ == "__main__":
    sys.exit(main())
