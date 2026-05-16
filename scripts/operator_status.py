"""Print standalone Crypto Hunter operator status."""

from __future__ import annotations

import json

from app.operator.operator_service import OperatorService


def main() -> None:
    """Print safe operator status."""
    print(json.dumps(OperatorService().get_operator_status(), indent=2))


if __name__ == "__main__":
    main()
