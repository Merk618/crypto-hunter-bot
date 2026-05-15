"""Equity curve builder tests."""

from app.reporting.equity_curve_builder import EquityCurveBuilder


def test_equity_curve_builder_handles_account_snapshots() -> None:
    """Builder creates points from snapshots."""
    report = EquityCurveBuilder().build_from_account_snapshots(
        [
            {"created_at": "2", "equity": 120, "cash_balance": 100, "realized_pnl": 20, "unrealized_pnl": 0},
            {"created_at": "1", "equity": 100, "cash_balance": 100, "realized_pnl": 0, "unrealized_pnl": 0},
        ]
    )
    assert len(report.points) == 2
    assert report.starting_equity == 100


def test_equity_curve_builder_calculates_return_percentage() -> None:
    """Builder calculates return."""
    report = EquityCurveBuilder().build_from_points([{"timestamp": "1", "equity": 100}, {"timestamp": "2", "equity": 125}])
    assert report.total_return_pct == 25


def test_equity_curve_builder_calculates_max_drawdown() -> None:
    """Builder calculates drawdown."""
    report = EquityCurveBuilder().build_from_points([{"timestamp": "1", "equity": 100}, {"timestamp": "2", "equity": 80}])
    assert report.max_drawdown_pct == 20
