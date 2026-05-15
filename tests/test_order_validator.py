"""Order validator tests."""

from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.execution.order_intent import OrderIntent
from app.execution.order_validator import OrderValidator


def make_settings(**overrides) -> Settings:
    """Create isolated settings for validator tests."""
    values = {
        "REQUIRE_MARKET_DATA_FRESHNESS": False,
        "REQUIRE_ACCOUNT_BALANCE_CHECK": False,
        "REQUIRE_SPREAD_CHECK": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def make_intent(**overrides) -> OrderIntent:
    """Create a valid baseline order intent."""
    values = {
        "symbol": "BTC/USD",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.001,
        "estimated_price": 65000,
        "reason": "validator test",
        "signal_score": 84,
        "signal_category": "STRONG_BUY",
        "risk_approved": True,
    }
    values.update(overrides)
    return OrderIntent(**values)


def fresh_ticker(spread_bps: float = 10) -> dict:
    """Create a fresh ticker with approximate spread."""
    mid = 65000
    half_spread = mid * (spread_bps / 10000) / 2
    return {
        "bid": mid - half_spread,
        "ask": mid + half_spread,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def test_validator_rejects_invalid_side() -> None:
    """Only buy and sell sides are valid."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(side="hold"), None)
    assert result.approved is False
    assert "side must be buy or sell" in result.blockers


def test_validator_rejects_invalid_order_type() -> None:
    """Only market order intents are supported."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(order_type="limit"), None)
    assert "only market order intents are supported" in result.blockers


def test_validator_rejects_zero_quantity() -> None:
    """Quantity must be positive."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(quantity=0), None)
    assert "quantity must be greater than zero" in result.blockers


def test_validator_rejects_zero_price() -> None:
    """Estimated price must be positive."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(estimated_price=0), None)
    assert "estimated price must be greater than zero" in result.blockers


def test_validator_rejects_below_minimum_notional() -> None:
    """Order notional must meet the configured minimum."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(quantity=0.00001), None)
    assert "estimated notional below minimum" in result.blockers


def test_validator_rejects_above_maximum_notional() -> None:
    """Order notional must stay below the configured maximum."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(quantity=0.01), None)
    assert "estimated notional above maximum" in result.blockers


def test_validator_rejects_missing_risk_approval() -> None:
    """Risk approval is mandatory by default."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(risk_approved=False), {"approved": False})
    assert "risk approval is required" in result.blockers


def test_validator_rejects_low_signal_score() -> None:
    """Signal score must meet the trade threshold."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(signal_score=60), None)
    assert "signal score below trade threshold" in result.blockers


def test_validator_rejects_non_strong_buy_for_buy_intent() -> None:
    """Buy intents require STRONG_BUY signals."""
    result = OrderValidator(make_settings()).validate_order_intent(make_intent(signal_category="BUY_WATCH"), None)
    assert "buy intent requires STRONG_BUY signal category" in result.blockers


def test_validator_rejects_stale_ticker_data() -> None:
    """Fresh market data is required when freshness checking is enabled."""
    ticker = fresh_ticker()
    ticker["timestamp"] = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    settings = make_settings(REQUIRE_MARKET_DATA_FRESHNESS=True, REQUIRE_SPREAD_CHECK=True)
    result = OrderValidator(settings).validate_order_intent(make_intent(), None, ticker=ticker)
    assert "ticker data is stale" in result.blockers


def test_validator_rejects_high_spread() -> None:
    """Spread must stay within the slippage threshold."""
    settings = make_settings(REQUIRE_MARKET_DATA_FRESHNESS=True, REQUIRE_SPREAD_CHECK=True)
    result = OrderValidator(settings).validate_order_intent(make_intent(), None, ticker=fresh_ticker(spread_bps=120))
    assert "spread exceeds allowed slippage" in result.blockers


def test_validator_rejects_insufficient_balance() -> None:
    """Buy orders require enough available cash when balance checks are enabled."""
    settings = make_settings(REQUIRE_ACCOUNT_BALANCE_CHECK=True)
    result = OrderValidator(settings).validate_order_intent(make_intent(), None, account_summary={"cash_balance": 10})
    assert "insufficient cash balance" in result.blockers


def test_validator_validates_approved_dry_run_order() -> None:
    """A clean dry-run order intent can pass all checks."""
    settings = make_settings(REQUIRE_MARKET_DATA_FRESHNESS=True, REQUIRE_ACCOUNT_BALANCE_CHECK=True, REQUIRE_SPREAD_CHECK=True)
    result = OrderValidator(settings).validate_order_intent(
        make_intent(),
        {"approved": True},
        account_summary={"cash_balance": 1000},
        ticker=fresh_ticker(),
        asset_pair_constraints={"min_quantity": 0.0001, "min_notional": 5, "quantity_decimals": 8},
    )

    assert result.approved is True
    assert result.approved_quantity == 0.001
    assert result.blockers == []
