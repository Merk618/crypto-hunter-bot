"""Dashboard reporting service."""

from __future__ import annotations

from datetime import datetime, timezone

from app.bot.bot_state import BotState
from app.execution.paper_broker import PaperBroker
from app.reporting.equity_curve_builder import EquityCurveBuilder
from app.reporting.performance_summary import (
    calculate_basic_win_rate_from_fills_or_trades,
    calculate_profit_factor_from_closed_trades,
    calculate_return_pct,
    rank_symbols_by_latest_signal,
    summarize_signals,
)
from app.reporting.report_models import DashboardOverview, PaperPerformanceReport, RecentActivityReport, RiskSummaryReport, SignalPerformanceReport
from app.risk.risk_manager import RiskManager
from app.storage.trade_journal import TradeJournal


class DashboardService:
    """Read-only dashboard data aggregator."""

    def __init__(self, bot_state: BotState | None = None, paper_broker: PaperBroker | None = None, risk_manager: RiskManager | None = None, trade_journal: TradeJournal | None = None) -> None:
        """Initialize dashboard dependencies."""
        self.bot_state = bot_state or BotState()
        self.paper_broker = paper_broker or PaperBroker()
        self.risk_manager = risk_manager or RiskManager()
        self.trade_journal = trade_journal or TradeJournal()
        self.equity_builder = EquityCurveBuilder()

    def get_overview(self) -> DashboardOverview:
        """Return overview report."""
        account = self._safe(lambda: self.paper_broker.get_account_summary(), {})
        signals_today = len(self._safe(lambda: self.trade_journal.get_recent_signals(limit=500), []))
        trades_today = int(account.get("fills", 0) or 0)
        risk_status = self.get_risk_summary().to_dict()
        state = self.bot_state.to_dict()
        return DashboardOverview(
            bot_status=state,
            mode=state.get("mode", "paper"),
            is_running=bool(state.get("is_running", False)),
            is_paused=bool(state.get("is_paused", False)),
            paper_equity=float(account.get("equity", 0) or 0),
            paper_cash=float(account.get("cash_balance", 0) or 0),
            open_positions_count=int(account.get("open_positions", 0) or 0),
            total_realized_pnl=float(account.get("realized_pnl", 0) or 0),
            total_unrealized_pnl=float(account.get("unrealized_pnl", 0) or 0),
            total_fees_paid=float(account.get("total_fees_paid", 0) or 0),
            signals_today=signals_today,
            trades_today=trades_today,
            risk_status=risk_status,
            kill_switch_active=bool(risk_status.get("kill_switch_active", False)),
            last_scan_at=state.get("last_scan_at"),
            last_error=state.get("last_error"),
        )

    def get_paper_performance(self) -> PaperPerformanceReport:
        """Return paper performance report."""
        account = self._safe(lambda: self.paper_broker.get_account_summary(), {})
        positions = self._safe(lambda: self.trade_journal.get_recent_positions(), [])
        closed_positions = [position for position in positions if position.get("status") == "closed"]
        fills = self._safe(lambda: self.trade_journal.get_recent_fills(limit=500), [])
        orders = self._safe(lambda: self.trade_journal.get_recent_orders(limit=500), [])
        starting = float(account.get("starting_cash", 0) or 0)
        equity = float(account.get("equity", 0) or 0)
        return PaperPerformanceReport(
            starting_cash=starting,
            current_equity=equity,
            cash_balance=float(account.get("cash_balance", 0) or 0),
            total_return_pct=calculate_return_pct(starting, equity),
            realized_pnl=float(account.get("realized_pnl", 0) or 0),
            unrealized_pnl=float(account.get("unrealized_pnl", 0) or 0),
            total_fees_paid=float(account.get("total_fees_paid", 0) or 0),
            open_positions=int(account.get("open_positions", 0) or 0),
            closed_positions=len(closed_positions),
            total_orders=len(orders),
            total_fills=len(fills),
            win_rate_if_available=calculate_basic_win_rate_from_fills_or_trades(closed_positions),
            profit_factor_if_available=calculate_profit_factor_from_closed_trades(closed_positions),
        )

    def get_signal_performance(self, limit: int = 100) -> SignalPerformanceReport:
        """Return signal performance report."""
        signals = self._safe(lambda: self.trade_journal.get_recent_signals(limit=limit), [])
        summary = summarize_signals(signals)
        return SignalPerformanceReport(
            **summary,
            symbols_ranked_by_latest_score=rank_symbols_by_latest_signal(signals),
            recent_signals=signals,
        )

    def get_risk_summary(self) -> RiskSummaryReport:
        """Return risk summary report."""
        settings = self.risk_manager.settings
        decisions = self._safe(lambda: self.trade_journal.get_recent_risk_decisions(limit=100), [])
        rejections = [decision for decision in decisions if not decision.get("approved")]
        blockers = []
        for decision in rejections:
            blockers.extend(decision.get("blockers") or [])
        return RiskSummaryReport(
            kill_switch_active=self.risk_manager.kill_switch.is_active(),
            max_risk_per_trade=settings.max_risk_per_trade,
            max_daily_loss=settings.max_daily_loss,
            max_open_positions=settings.max_open_positions,
            max_position_allocation=settings.max_position_allocation,
            min_signal_score_to_trade=settings.min_signal_score_to_trade,
            active_cooldowns=[],
            recent_risk_rejections=rejections[:20],
            recent_blockers=list(dict.fromkeys(blockers))[:20],
        )

    def get_recent_activity(self, limit: int = 50) -> RecentActivityReport:
        """Return recent activity report."""
        return RecentActivityReport(
            recent_events=self._safe(lambda: self.trade_journal.get_recent_bot_events(limit), []),
            recent_orders=self._safe(lambda: self.trade_journal.get_recent_orders(limit), []),
            recent_fills=self._safe(lambda: self.trade_journal.get_recent_fills(limit), []),
            recent_signals=self._safe(lambda: self.trade_journal.get_recent_signals(limit), []),
            recent_errors=self._safe(lambda: self.trade_journal.get_recent_errors(limit), []),
        )

    def get_equity_curve(self, limit: int = 500):
        """Return equity curve report."""
        snapshots = self._safe(lambda: self.trade_journal.get_recent_account_snapshots(limit), [])
        return self.equity_builder.build_from_account_snapshots(snapshots)

    def get_full_dashboard_snapshot(self) -> dict:
        """Return full dashboard snapshot."""
        return {
            "overview": self.get_overview().to_dict(),
            "paper_performance": self.get_paper_performance().to_dict(),
            "signal_performance": self.get_signal_performance().to_dict(),
            "risk_summary": self.get_risk_summary().to_dict(),
            "recent_activity": self.get_recent_activity().to_dict(),
            "equity_curve": self.get_equity_curve().to_dict(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _safe(self, fn, default):
        """Return default when optional storage is unavailable."""
        try:
            return fn()
        except Exception:
            return default
