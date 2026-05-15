"""Dry-run execution preview."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.execution.order_intent import OrderIntent, OrderValidationResult
from app.storage.trade_journal import TradeJournal


class DryRunExecutor:
    """Preview orders without calling any live broker."""

    def __init__(self, settings: Settings | None = None, journal: TradeJournal | None = None) -> None:
        """Initialize dry-run executor."""
        self.settings = settings or get_settings()
        self.journal = journal
        self._dry_runs: list[dict] = []

    def preview_order(self, intent: OrderIntent, validation_result: OrderValidationResult) -> dict:
        """Return what would be sent to an exchange, marked DRY_RUN."""
        fee = intent.estimated_notional * self.settings.paper_fee_rate
        slippage = intent.estimated_notional * (self.settings.max_allowed_slippage_bps / 10000)
        return {
            "status": "DRY_RUN",
            "would_send": {
                "symbol": validation_result.normalized_symbol,
                "side": intent.side,
                "order_type": intent.order_type,
                "quantity": validation_result.approved_quantity,
            },
            "approved": validation_result.approved,
            "intent": intent.to_dict(),
            "validation": validation_result.to_dict(),
            "estimated_fee": fee,
            "estimated_slippage": slippage,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def execute_dry_run(self, intent: OrderIntent, validation_result: OrderValidationResult) -> dict:
        """Record and return a dry-run order preview."""
        preview = self.preview_order(intent, validation_result)
        self._dry_runs.append(preview)
        if self.journal:
            try:
                self.journal.record_bot_event("dry_run_order", "Dry-run order preview", preview)
            except Exception:
                pass
        return preview

    def get_recent_dry_runs(self, limit: int = 50) -> list[dict]:
        """Return recent dry runs."""
        return list(reversed(self._dry_runs[-limit:]))
