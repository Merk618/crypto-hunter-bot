"""Run Phase 22 read-only real-data validation."""

from __future__ import annotations

import json
import sys

from app.validation.real_data_validator import RealDataValidator


def main() -> int:
    """Print full validation report and return process status."""
    report = RealDataValidator().run_all_checks()
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
