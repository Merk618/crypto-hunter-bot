"""Position sizer tests."""

import pytest

from app.risk.position_sizer import PositionSizer, PositionSizingError


def test_position_sizer_calculates_quantity_correctly() -> None:
    """Quantity equals risk amount divided by risk per unit."""
    qty = PositionSizer().calculate_quantity_by_risk(10000, 100, 90, 0.01)
    assert qty == pytest.approx(10.0)


def test_position_sizer_rejects_invalid_prices_or_equity() -> None:
    """Invalid sizing inputs raise clear errors."""
    sizer = PositionSizer()
    with pytest.raises(PositionSizingError):
        sizer.calculate_quantity_by_risk(0, 100, 90, 0.01)
    with pytest.raises(PositionSizingError):
        sizer.calculate_quantity_by_risk(10000, 0, 90, 0.01)
    with pytest.raises(PositionSizingError):
        sizer.calculate_quantity_by_risk(10000, 100, 0, 0.01)
    with pytest.raises(PositionSizingError):
        sizer.calculate_quantity_by_risk(10000, 100, 90, 0.06)


def test_position_sizer_caps_quantity_by_cash() -> None:
    """Cash cap accounts for fees."""
    qty = PositionSizer().cap_quantity_by_cash(10, cash_balance=100, entry_price=10, fee_rate=0.01)
    assert qty == pytest.approx(100 / 10.1)


def test_position_sizer_caps_quantity_by_allocation() -> None:
    """Allocation cap limits position notional."""
    qty = PositionSizer().cap_quantity_by_allocation(100, equity=10000, entry_price=100, max_allocation=0.25)
    assert qty == pytest.approx(25.0)
