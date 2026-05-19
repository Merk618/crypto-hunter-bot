"""Print local operator startup guide and health summary."""

from __future__ import annotations

import json

from app.operator.local_runbook import LocalOperatorRunbookService


def main() -> None:
    """Print startup guide and health summary."""
    service = LocalOperatorRunbookService()
    print(json.dumps({"startup_guide": service.startup_guide(), "health": service.one_command_health_check()}, indent=2))


if __name__ == "__main__":
    main()
