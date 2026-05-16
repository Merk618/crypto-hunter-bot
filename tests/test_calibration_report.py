"""Calibration report tests."""

from app.diagnostics.calibration_report import CalibrationReport
from app.main import app


def test_calibration_report_summarizes_signal_results() -> None:
    """Calibration can turn signal dictionaries into report rows."""
    report = CalibrationReport().summarize(
        [
            {
                "symbol": "BTC/USD",
                "timeframe": "1h",
                "latest_price": 100,
                "score": 84,
                "category": "STRONG_BUY",
                "risk_level": "LOW",
                "blockers": [],
                "warnings": [],
            }
        ]
    )

    assert report["overall_status"] == "NORMAL"
    assert report["source"] == "crypto_hunter_phase14_calibration_report"


def test_calibration_report_handles_no_signals_cleanly() -> None:
    """Empty calibration inputs are data-unavailable."""
    report = CalibrationReport().summarize([])

    assert report["passed"] is False
    assert report["overall_status"] == "DATA_UNAVAILABLE"


def test_calibration_report_labels_too_strict() -> None:
    """Synthetic strictness helper detects no bullish coverage."""
    status = CalibrationReport().synthetic_strictness_check([{"category": "WEAK", "risk_level": "HIGH"}])

    assert status == "TOO_STRICT"


def test_calibration_report_labels_normal() -> None:
    """Synthetic strictness helper accepts balanced bullish coverage."""
    status = CalibrationReport().synthetic_strictness_check([{"category": "BUY_WATCH", "risk_level": "MEDIUM"}])

    assert status == "NORMAL"


def test_calibration_report_labels_too_loose() -> None:
    """Strong buy with extreme risk is too permissive."""
    status = CalibrationReport().synthetic_strictness_check([{"category": "STRONG_BUY", "risk_level": "EXTREME"}])

    assert status == "TOO_LOOSE"


def test_calibration_report_labels_blocked() -> None:
    """Blocked signals are marked blocked."""
    row = CalibrationReport().from_signal(
        {
            "symbol": "BTC/USD",
            "timeframe": "1h",
            "latest_price": 100,
            "score": 84,
            "category": "STRONG_BUY",
            "risk_level": "HIGH",
            "blockers": ["close at or below EMA 200"],
            "warnings": [],
        }
    )

    assert row.calibration_status == "BLOCKED"


def test_calibration_report_labels_data_unavailable() -> None:
    """Missing signal category is data-unavailable."""
    status, notes = CalibrationReport().classify_signal({})

    assert status == "DATA_UNAVAILABLE"
    assert notes


def test_diagnostics_endpoints_exist() -> None:
    """Diagnostics routes are registered."""
    paths = {route.path for route in app.routes}

    assert "/diagnostics/smoke-test" in paths
    assert "/diagnostics/calibration-report" in paths


def test_diagnostics_endpoints_do_not_expose_secrets() -> None:
    """Diagnostics route names are safe."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/diagnostics"))

    assert "secret" not in paths
    assert "api_key" not in paths


def test_no_live_trading_or_withdrawal_diagnostics_routes_exist() -> None:
    """Diagnostics add no live or withdrawal routes."""
    paths = {route.path.lower() for route in app.routes}

    assert not any(path.startswith("/live") for path in paths)
    assert not any("withdraw" in path for path in paths)
