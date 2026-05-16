"""Read-only alert channels."""

from __future__ import annotations

from app.alerts.alert_models import AlertSendResult
from app.config import Settings, get_settings


class ConsoleAlertChannel:
    """Console alert channel for local previews."""

    def send(self, message: str, enabled: bool) -> AlertSendResult:
        """Return a send result without external side effects."""
        if not enabled:
            return AlertSendResult("console", attempted=False, sent=False, message="Console alerts disabled").to_dict()
        return AlertSendResult("console", attempted=True, sent=True, message=message).to_dict()


class DiscordDryRunChannel:
    """Discord dry-run channel that never calls external webhooks."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize channel settings."""
        self.settings = settings or get_settings()

    def dry_run(self, message: str) -> AlertSendResult:
        """Return what would be sent without exposing or calling webhook URLs."""
        warnings: list[str] = []
        if not self.settings.alert_channel_discord:
            warnings.append("Discord channel disabled")
        if not self.settings.discord_webhook_url:
            warnings.append("Discord webhook not configured")
        return AlertSendResult(
            channel="discord",
            attempted=False,
            sent=False,
            message=f"DRY_RUN: {message[:500]}",
            warnings=warnings,
        )
