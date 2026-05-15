"""Dry-run executor tests."""

from app.config import Settings
from app.execution.dry_run_executor import DryRunExecutor
from app.execution.order_intent import OrderIntent, OrderValidationResult


def make_intent() -> OrderIntent:
    """Create a test order intent."""
    return OrderIntent(
        symbol="BTC/USD",
        side="buy",
        order_type="market",
        quantity=0.001,
        estimated_price=65000,
        reason="dry run test",
        signal_score=84,
        signal_category="STRONG_BUY",
        risk_approved=True,
    )


def make_validation(intent: OrderIntent) -> OrderValidationResult:
    """Create an approved validation result."""
    return OrderValidationResult(
        approved=True,
        intent_id=intent.intent_id,
        symbol=intent.symbol,
        side=intent.side,
        normalized_symbol="BTC/USD",
        approved_quantity=intent.quantity,
        estimated_price=intent.estimated_price,
        estimated_notional=intent.estimated_notional,
        blockers=[],
        warnings=[],
        checks={},
    )


def test_dry_run_executor_returns_dry_run_status() -> None:
    """Dry-run previews are clearly marked and do not imply live execution."""
    intent = make_intent()
    preview = DryRunExecutor(Settings(_env_file=None)).execute_dry_run(intent, make_validation(intent))

    assert preview["status"] == "DRY_RUN"
    assert preview["would_send"]["symbol"] == "BTC/USD"
    assert preview["approved"] is True


def test_dry_run_executor_does_not_call_live_broker() -> None:
    """DryRunExecutor has no live broker dependency to call."""
    executor = DryRunExecutor(Settings(_env_file=None))
    intent = make_intent()

    executor.execute_dry_run(intent, make_validation(intent))

    assert not hasattr(executor, "live_broker")
    assert len(executor.get_recent_dry_runs()) == 1
