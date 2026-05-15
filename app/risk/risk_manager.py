"""Risk validation for proposed trades."""

from app.config import Settings, get_settings
from app.risk.kill_switch import KillSwitch


class RiskManager:
    """Validate risk limits before execution."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize risk manager state."""
        self.settings = settings or get_settings()
        self.kill_switch = KillSwitch(max_daily_loss=self.settings.max_daily_loss)

    def can_open_position(self, open_positions: int, risk_fraction: float) -> bool:
        """Return True when position count and per-trade risk are within limits."""
        if self.kill_switch.is_active():
            return False
        if open_positions >= self.settings.max_open_positions:
            return False
        return risk_fraction <= self.settings.max_risk_per_trade
