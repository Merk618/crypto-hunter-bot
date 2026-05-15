"""Order intent model tests."""

from app.execution.order_intent import OrderIntent


def test_order_intent_calculates_estimated_notional() -> None:
    """OrderIntent exposes quantity times estimated price as notional."""
    intent = OrderIntent(
        symbol="BTC/USD",
        side="buy",
        order_type="market",
        quantity=0.002,
        estimated_price=50000,
        reason="unit test",
        signal_score=84,
        signal_category="STRONG_BUY",
        risk_approved=True,
    )

    assert intent.estimated_notional == 100
    assert intent.to_dict()["estimated_notional"] == 100
    assert intent.to_dict()["source"] == "crypto_hunter_order_intent_v1"
