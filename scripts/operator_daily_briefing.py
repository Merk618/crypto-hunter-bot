"""Print standalone daily operator briefing."""

from __future__ import annotations

import json

from app.operator.operator_service import OperatorService


def main() -> None:
    """Print daily briefing."""
    print(json.dumps(OperatorService().get_daily_operator_briefing(), indent=2))


if __name__ == "__main__":
    main()
