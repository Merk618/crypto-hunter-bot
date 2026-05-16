"""Run the Phase 14 local smoke test from the command line."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.diagnostics.calibration_report import CalibrationReport  # noqa: E402
from app.diagnostics.smoke_test_runner import SmokeTestRunner  # noqa: E402


def main() -> int:
    """Run safe diagnostics and print a compact summary."""
    settings = get_settings()
    smoke = SmokeTestRunner(settings=settings).run(allow_paper_scan=settings.phase14_allow_paper_scan)
    calibration = CalibrationReport(settings=settings).analyze_symbols()
    summary = {
        "smoke_passed": smoke["passed"],
        "live_trading_locked": smoke["live_trading_locked"],
        "safety_audit_passed": smoke["safety_audit_passed"],
        "symbols_checked": smoke["symbols_checked"],
        "signals_generated": smoke["signals_generated"],
        "calibration_status": calibration["overall_status"],
        "calibration_notes": calibration["notes"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if smoke["live_trading_locked"] and smoke["safety_audit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
