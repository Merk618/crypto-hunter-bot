"""Controlled paper observation tests."""

from app.config import Settings
from app.observation.controlled_paper_models import ControlledPaperObservationRequest
from app.observation.controlled_paper_observation import ControlledPaperObservationService


def settings(**updates):
    """Build settings with safe overrides."""
    return Settings(_env_file=None).model_copy(update=updates)


def result(symbol="BTC/USD", category="STRONG_BUY", approved=True):
    """Build observation result."""
    return {
        "symbol": symbol,
        "signal": {"symbol": symbol, "score": 84 if category == "STRONG_BUY" else 54, "category": category, "latest_price": 100.0},
        "risk_decision": {"approved": approved, "estimated_notional": 100.0},
    }


def runs(category="STRONG_BUY", approved=True):
    """Build completed observation runs."""
    return [{"run_id": "run-1", "status": "completed", "results": [result("BTC/USD", category, approved), result("ETH/USD", category, approved)]}]


class Approval:
    """Approval fake."""

    def __init__(self, status="ELIGIBLE_FOR_OPERATOR_REVIEW"):
        self.status = status

    def evaluate(self, runs=None):
        return {"approval_status": self.status, "eligible_for_operator_review": self.status == "ELIGIBLE_FOR_OPERATOR_REVIEW"}


class Fresh:
    """Fresh fake."""

    def __init__(self, passed=True):
        self.passed = passed

    def validate(self, runs=None):
        return {"passed": self.passed, "status": "PASSED" if self.passed else "INSUFFICIENT_DATA"}


class Risk:
    """Risk hygiene fake."""

    def __init__(self, clean=True):
        self.clean = clean

    def legacy_aware_readiness(self):
        return {"current_clean": self.clean, "legacy_present": False}


class Readiness:
    """Readiness fake."""

    def check(self, runs=None):
        return {"decision": "OBSERVE_ONLY"}


class Executor:
    """Paper executor fake."""

    def __init__(self):
        self.calls = []

    def execute_paper_market_order(self, symbol, side, quantity, market_price, reason=None):
        self.calls.append((symbol, side, quantity, market_price, reason))
        return {"accepted": True, "order": {"symbol": symbol}, "message": "Paper buy filled"}


def service(**kwargs):
    """Build controlled service."""
    return ControlledPaperObservationService(
        settings=kwargs.pop("settings", settings()),
        approval_gate=kwargs.pop("approval_gate", Approval()),
        fresh_validator=kwargs.pop("fresh_validator", Fresh()),
        risk_hygiene=kwargs.pop("risk_hygiene", Risk()),
        readiness=kwargs.pop("readiness", Readiness()),
        trade_executor=kwargs.pop("trade_executor", Executor()),
    )


def request(**kwargs):
    """Build request."""
    data = {"manual_start": True, "operator_acknowledged": True, "allow_paper_trade_preview": True, "allow_paper_trade_execution": False}
    data.update(kwargs)
    return ControlledPaperObservationRequest(**data)


def enabled_settings(**updates):
    """Build enabled controlled paper settings for synthetic tests."""
    data = {
        "controlled_paper_observation_enabled": True,
        "paper_trade_observation_enabled": True,
        "controlled_paper_observation_allow_buys": True,
    }
    data.update(updates)
    return settings(**data)


def test_controlled_paper_status_disabled_by_default() -> None:
    """Controlled paper is disabled by default."""
    status = service().status()

    assert status["enabled"] is False
    assert status["paper_trade_observation_enabled"] is False


def test_run_once_refuses_when_manual_start_false() -> None:
    """Manual start is required."""
    report = service(settings=enabled_settings()).run_once(request(manual_start=False), runs=runs())

    assert "manual_start=true is required" in report["blockers"]
    assert report["paper_trades_created"] == 0


def test_run_once_refuses_when_operator_acknowledged_false() -> None:
    """Operator acknowledgement is required."""
    report = service(settings=enabled_settings()).run_once(request(operator_acknowledged=False), runs=runs())

    assert "operator_acknowledged=true is required" in report["blockers"]
    assert report["paper_trades_created"] == 0


def test_run_once_refuses_when_config_disabled() -> None:
    """Disabled config blocks execution."""
    report = service().run_once(request(), runs=runs())

    assert report["status"] == "DISABLED_BY_CONFIG"
    assert report["paper_trades_created"] == 0


def test_blocks_when_approval_gate_not_eligible() -> None:
    """Approval gate must be eligible."""
    decision = service(settings=enabled_settings(), approval_gate=Approval("NOT_READY")).evaluate(request(), runs())

    assert decision["status"] == "BLOCKED_BY_APPROVAL_GATE"


def test_blocks_when_fresh_validation_fails() -> None:
    """Fresh validation must pass."""
    decision = service(settings=enabled_settings(), fresh_validator=Fresh(False)).evaluate(request(), runs())

    assert decision["status"] == "BLOCKED_BY_FRESH_VALIDATION"


def test_blocks_when_current_risk_hygiene_fails() -> None:
    """Current risk hygiene must be clean."""
    decision = service(settings=enabled_settings(), risk_hygiene=Risk(False)).evaluate(request(), runs())

    assert decision["status"] == "BLOCKED_BY_RISK_HYGIENE"


def test_blocks_when_no_strong_buy_signals_exist() -> None:
    """Strong buy signals are required."""
    decision = service(settings=enabled_settings()).evaluate(request(), runs(category="NEUTRAL"))

    assert decision["status"] == "NOT_READY"


def test_blocks_when_no_risk_approved_signals_exist() -> None:
    """Risk approval is required."""
    decision = service(settings=enabled_settings()).evaluate(request(), runs(approved=False))

    assert decision["status"] == "NOT_READY"


def test_preview_generates_without_paper_trade() -> None:
    """Preview does not create paper trades."""
    preview = service(settings=enabled_settings()).preview(request(), runs())

    assert preview["previews"]
    assert preview["paper_trades_created"] == 0


def test_preview_caps_notional() -> None:
    """Preview caps notional to configured maximum."""
    preview = service(settings=enabled_settings(controlled_paper_observation_max_notional_per_trade=25)).preview(request(), runs())

    assert preview["previews"][0]["requested_notional"] == 100.0
    assert preview["previews"][0]["capped_notional"] == 25.0


def test_run_once_creates_zero_paper_trades_by_default() -> None:
    """Default config creates zero paper trades."""
    report = service().run_once(request(allow_paper_trade_execution=True), runs())

    assert report["paper_trades_created"] == 0


def test_even_eligible_requires_config_and_request_allowance() -> None:
    """Eligible gates still need explicit config and request."""
    report = service(settings=enabled_settings(controlled_paper_observation_allow_buys=False)).run_once(request(allow_paper_trade_execution=True), runs())

    assert report["paper_trades_created"] == 0


def test_synthetic_enabled_routes_only_through_paper_executor() -> None:
    """Synthetic execution uses paper executor only."""
    executor = Executor()
    report = service(settings=enabled_settings(), trade_executor=executor).run_once(request(allow_paper_trade_execution=True), runs())

    assert report["paper_trades_created"] == 1
    assert executor.calls
    assert report["trade_results"][0]["broker"] == "PAPER"
    assert report["trade_results"][0]["real_execution"] is False
    assert report["trade_results"][0]["live_trade"] is False


def test_max_trades_per_run_enforced() -> None:
    """Max trades per run is enforced."""
    executor = Executor()
    report = service(settings=enabled_settings(controlled_paper_observation_max_trades_per_run=1), trade_executor=executor).run_once(request(allow_paper_trade_execution=True, max_trades=10), runs())

    assert report["paper_trades_created"] == 1


def test_max_trades_per_day_enforced() -> None:
    """Max trades per day is enforced."""
    executor = Executor()
    svc = service(settings=enabled_settings(controlled_paper_observation_max_trades_per_day=1), trade_executor=executor)
    first = svc.run_once(request(allow_paper_trade_execution=True), runs())
    second = svc.run_once(request(allow_paper_trade_execution=True), runs())

    assert first["paper_trades_created"] == 1
    assert second["paper_trades_created"] == 0
