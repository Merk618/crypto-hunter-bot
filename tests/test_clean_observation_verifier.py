"""Clean observation verification tests."""

from app.observation.clean_observation_verifier import CleanObservationVerifier


def risk_record(**kwargs):
    """Build synthetic risk decision."""
    data = {
        "symbol": "BTC/USD",
        "side": "buy",
        "approved": False,
        "approved_quantity": None,
        "max_quantity": None,
        "risk_amount": None,
        "estimated_notional": None,
        "blockers": ["signal score below minimum"],
        "reasons": [],
        "warnings": [],
        "source": "crypto_hunter_risk_v1",
    }
    data.update(kwargs)
    return data


def run_with_results(results, run_id="run-1"):
    """Build completed observation run."""
    return {"run_id": run_id, "status": "completed", "results": results}


def result(symbol="BTC/USD", risk=None):
    """Build observation result."""
    return {"symbol": symbol, "risk_decision": risk or risk_record(symbol=symbol)}


def clean_runs():
    """Build enough clean runs/results."""
    return [
        run_with_results([result("BTC/USD"), result("ETH/USD"), result("SOL/USD"), result("SUI/USD")], "run-1"),
        run_with_results([result("BTC/USD"), result("ETH/USD"), result("SOL/USD"), result("SUI/USD")], "run-2"),
    ]


def test_clean_verifier_passes_with_clean_post_phase31_rejected_records() -> None:
    """Clean rejected records pass verification."""
    report = CleanObservationVerifier().verify(runs=clean_runs())

    assert report["passed"] is True
    assert report["clean_rejected_count"] == 8
    assert report["current_inconsistency_count"] == 0


def test_clean_verifier_fails_with_current_inconsistent_rejected_record() -> None:
    """Current inconsistent rejected records fail verification."""
    bad = result("BTC/USD", risk_record(source="crypto_hunter_risk_v2", approved_quantity=1.0))
    runs = [run_with_results([bad, result("ETH/USD"), result("SOL/USD"), result("SUI/USD")], "run-1"), clean_runs()[1]]
    report = CleanObservationVerifier().verify(runs=runs)

    assert report["passed"] is False
    assert report["current_inconsistency_count"] == 1


def test_clean_verifier_reports_insufficient_data() -> None:
    """Too little post-remediation observation data returns blockers."""
    report = CleanObservationVerifier().verify(runs=[run_with_results([result("BTC/USD")])])

    assert report["passed"] is False
    assert report["completed_runs_checked"] == 1
    assert report["observation_results_checked"] == 1
    assert report["blockers"]


def test_clean_verifier_reports_legacy_warnings() -> None:
    """Legacy inconsistent records warn but are reported separately."""
    legacy = result("BTC/USD", risk_record(approved_quantity=1.0, risk_amount=10.0))
    runs = [run_with_results([legacy, result("ETH/USD"), result("SOL/USD"), result("SUI/USD")], "run-1"), clean_runs()[1]]
    report = CleanObservationVerifier().verify(runs=runs)

    assert report["legacy_inconsistency_count"] == 1
    assert any("Legacy risk records" in warning for warning in report["warnings"])
