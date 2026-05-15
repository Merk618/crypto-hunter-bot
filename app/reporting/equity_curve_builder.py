"""Equity curve report builder."""

from __future__ import annotations

from app.reporting.performance_summary import calculate_return_pct
from app.reporting.report_models import EquityCurveReport


class EquityCurveBuilder:
    """Build equity curve reports from snapshots, backtests, or manual records."""

    def build_from_account_snapshots(self, snapshots: list[dict]) -> EquityCurveReport:
        """Build equity curve from account snapshots."""
        points = [
            {
                "timestamp": row.get("created_at") or row.get("timestamp"),
                "equity": float(row.get("equity") or 0),
                "cash": float(row.get("cash_balance") or row.get("cash") or 0),
                "realized_pnl": float(row.get("realized_pnl") or 0),
                "unrealized_pnl": float(row.get("unrealized_pnl") or 0),
            }
            for row in reversed(snapshots)
        ]
        return self.build_from_points(points)

    def build_from_backtest_points(self, points: list) -> EquityCurveReport:
        """Build equity curve from backtest equity points."""
        normalized = [point.to_dict() if hasattr(point, "to_dict") else dict(point) for point in points]
        return self.build_from_points(normalized)

    def build_from_points(self, points: list[dict]) -> EquityCurveReport:
        """Build report from generic equity records."""
        if not points:
            return EquityCurveReport([], 0.0, 0.0, 0.0, 0.0)
        peak = None
        max_drawdown = 0.0
        output = []
        for point in points:
            equity = float(point.get("equity") or 0)
            peak = equity if peak is None else max(peak, equity)
            drawdown = ((peak - equity) / peak) * 100 if peak and peak > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)
            row = dict(point)
            row["drawdown_pct"] = drawdown
            output.append(row)
        starting = float(output[0].get("equity") or 0)
        ending = float(output[-1].get("equity") or 0)
        return EquityCurveReport(output, starting, ending, calculate_return_pct(starting, ending), max_drawdown)
