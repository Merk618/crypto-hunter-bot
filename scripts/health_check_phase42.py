"""Run Phase 42 one-command health check."""

from __future__ import annotations

import json
import sys

from app.operator.local_runbook import LocalOperatorRunbookService


def main() -> int:
    """Print health check and return process status."""
    report = LocalOperatorRunbookService().one_command_health_check()
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
