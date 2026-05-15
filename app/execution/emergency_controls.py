"""Emergency controls for paper and dry-run safety."""

from __future__ import annotations

from datetime import datetime, timezone

from app.bot.bot_state import BotState
from app.config import Settings, get_settings
from app.execution.paper_broker import PaperBroker


class EmergencyControls:
    """Emergency controls that do not touch live exchanges."""

    def __init__(self, bot_state: BotState | None = None, paper_broker: PaperBroker | None = None, settings: Settings | None = None) -> None:
        """Initialize emergency controls."""
        self.bot_state = bot_state or BotState()
        self.paper_broker = paper_broker
        self.settings = settings or get_settings()

    def emergency_pause_bot(self, reason: str) -> dict:
        """Pause the bot."""
        self.bot_state.pause()
        return {"status": "paused", "reason": reason, "timestamp": datetime.now(timezone.utc).isoformat()}

    def emergency_stop_bot(self, reason: str) -> dict:
        """Stop the bot."""
        self.bot_state.stop()
        return {"status": "stopped", "reason": reason, "timestamp": datetime.now(timezone.utc).isoformat()}

    def emergency_flatten_paper_positions(self, reason: str, market_prices: dict | None = None) -> dict:
        """Close paper positions only when synthetic market prices are supplied."""
        if not self.paper_broker or not market_prices:
            return {"status": "dry_run", "reason": reason, "message": "No paper positions flattened without explicit market prices"}
        results = []
        for symbol, position in list(self.paper_broker.account.open_positions.items()):
            price = market_prices.get(symbol) or market_prices.get(symbol.replace("/", "-"))
            if price:
                results.append(self.paper_broker.close_position(symbol, float(price), reason).to_dict())
        return {"status": "paper_flattened", "results": results}

    def emergency_cancel_live_orders_dry_run(self, reason: str) -> dict:
        """Return dry-run live cancel intent without calling exchange cancel endpoints."""
        return {
            "status": "DRY_RUN",
            "reason": reason,
            "message": "No live cancel endpoint called in Phase 12",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def dead_man_switch_status(self) -> dict:
        """Return dead-man switch status."""
        return {
            "enabled": self.settings.dead_man_switch_enabled,
            "timeout_seconds": self.settings.dead_man_switch_timeout_seconds,
            "live_actions_enabled": False,
            "message": "Dead-man switch performs no live exchange actions in Phase 12",
        }
