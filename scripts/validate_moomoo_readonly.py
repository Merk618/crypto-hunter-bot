"""Validate MooMoo read-only health and Stock/Options Hunter responses."""

from __future__ import annotations

import json
import sys

from app.validation.real_data_validator import RealDataValidator
from app.validation.validation_report import build_validation_report


def main() -> int:
    """Print MooMoo read-only validation report."""
    validator = RealDataValidator()
    report = build_validation_report([
        validator.validate_moomoo_health(),
        validator.validate_stock_hunter(),
        validator.validate_options_scanner(),
    ]).to_dict()
    print(json.dumps(report, indent=2))
    return 0 if report.get("moomoo_readonly_passed") else 1


if __name__ == "__main__":
    sys.exit(main())
