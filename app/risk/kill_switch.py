"""Daily loss kill switch."""


class KillSwitch:
    """Track whether the bot should refuse new trades."""

    def __init__(self, max_daily_loss: float) -> None:
        """Initialize the kill switch threshold."""
        self.max_daily_loss = max_daily_loss
        self.enabled = False

    def update(self, daily_loss_fraction: float) -> bool:
        """Activate when daily loss reaches the configured threshold."""
        if daily_loss_fraction >= self.max_daily_loss:
            self.enabled = True
        return self.enabled

    def is_active(self) -> bool:
        """Return whether the kill switch is active."""
        return self.enabled
