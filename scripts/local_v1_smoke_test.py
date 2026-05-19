"""Run lightweight local Crypto Hunter v1 smoke test."""

from __future__ import annotations

import json
import sys

from app.operator.local_runbook import LocalOperatorRunbookService


def main() -> int:
    """Print local smoke test result."""
    report = LocalOperatorRunbookService().local_smoke_test()
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
