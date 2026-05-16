"""Run safe standalone startup checks."""

from __future__ import annotations

import json

from app.operator.operator_service import OperatorService


def main() -> None:
    """Print startup check summary."""
    print(json.dumps(OperatorService().run_startup_checks(), indent=2))


if __name__ == "__main__":
    main()
