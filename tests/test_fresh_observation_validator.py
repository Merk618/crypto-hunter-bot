"""Fresh observation validator tests."""

from app.observation.fresh_observation_validator import FreshObservationValidator


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


def result(symbol="BTC/USD", risk=None, category="NEUTRAL", paper_trade=False):
    """Build observation result."""
    data = {
        "symbol": symbol,
        "signal": {"symbol": symbol, "score": 54, "category": category},
        "risk_decision": risk if risk is not None else risk_record(symbol=symbol),
    }
    if paper_trade:
        data["paper_trade_result"] = {"accepted": True}
    return data


def run(run_id, results):
    """Build completed run."""
    return {
        "run_id": run_id,
        "status": "completed",
        "started_at": "2026-05-17T00:00:00+00:00",
        "completed_at": "2026-05-17T00:01:00+00:00",
        "results": results,
    }


def clean_runs(risk=None):
    """Build two completed runs with eight results."""
    return [
        run("run-1", [result("BTC/USD", risk), result("ETH/USD", risk), result("SOL/USD", risk), result("SUI/USD", risk)]),
        run("run-2", [result("BTC/USD", risk), result("ETH/USD", risk), result("SOL/USD", risk), result("SUI/USD", risk)]),
    ]


def test_fresh_validator_returns_insufficient_data_with_no_completed_runs() -> None:
    """No runs are insufficient."""
    report = FreshObservationValidator().validate(runs=[])

    assert report["passed"] is False
    assert report["status"] == "INSUFFICIENT_DATA"


def test_fresh_validator_returns_insufficient_data_with_too_few_results() -> None:
    """Too few results are insufficient."""
    report = FreshObservationValidator().validate(runs=[run("run-1", [result("BTC/USD")])])

    assert report["passed"] is False
    assert report["status"] == "INSUFFICIENT_DATA"


def test_fresh_validator_passes_with_clean_rejected_results() -> None:
    """Clean rejected results pass."""
    report = FreshObservationValidator().validate(runs=clean_runs())

    assert report["passed"] is True
    assert report["status"] == "PASSED"
    assert report["clean_rejected_count"] == 8
    assert report["paper_trade_observation_allowed_now"] is False
    assert report["live_review_allowed"] is False


def test_fresh_validator_passes_with_clean_approved_records() -> None:
    """Clean approved records pass."""
    approved = risk_record(approved=True, approved_quantity=0.1, max_quantity=0.1, risk_amount=25, blockers=[])
    report = FreshObservationValidator().validate(runs=clean_runs(approved))

    assert report["passed"] is True
    assert report["clean_approved_count"] == 8


def test_fresh_validator_fails_with_current_inconsistent_rejected_record() -> None:
    """Current inconsistent rejected records block."""
    current_bad = risk_record(source="crypto_hunter_risk_v2", approved_quantity=1.0)
    report = FreshObservationValidator().validate(runs=clean_runs(current_bad))

    assert report["passed"] is False
    assert report["status"] == "BLOCKED_CURRENT_RISK_INCONSISTENCY"
    assert report["current_inconsistency_count"] == 8


def test_fresh_validator_warns_but_passes_for_legacy_inconsistent_records() -> None:
    """Legacy inconsistencies warn but do not fail by default."""
    legacy_bad = risk_record(approved_quantity=1.0, risk_amount=10)
    report = FreshObservationValidator().validate(runs=clean_runs(legacy_bad))

    assert report["passed"] is True
    assert report["legacy_inconsistency_count"] == 8
    assert report["warnings"]


def test_fresh_validator_counts_paper_trades_but_does_not_enable() -> None:
    """Paper trades are counted without enabling trading."""
    runs = [run("run-1", [result("BTC/USD", paper_trade=True), result("ETH/USD"), result("SOL/USD"), result("SUI/USD")]), clean_runs()[1]]
    report = FreshObservationValidator().validate(runs=runs)

    assert report["paper_trades_created"] == 1
    assert report["paper_trade_observation_allowed_now"] is False
