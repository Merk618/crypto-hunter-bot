"""Read-only alert report service."""

from __future__ import annotations

from app.alerts.alert_channels import ConsoleAlertChannel, DiscordDryRunChannel
from app.alerts.alert_formatter import AlertFormatter
from app.alerts.alert_models import AlertReport
from app.config import Settings, get_settings
from app.reporting.unified_report_service import UnifiedReportService


class AlertService:
    """Build and preview alert reports without trading or external sends by default."""

    def __init__(
        self,
        settings: Settings | None = None,
        unified_report_service: UnifiedReportService | None = None,
        formatter: AlertFormatter | None = None,
        console_channel: ConsoleAlertChannel | None = None,
        discord_channel: DiscordDryRunChannel | None = None,
    ) -> None:
        """Initialize alert dependencies."""
        self.settings = settings or get_settings()
        self.unified_report_service = unified_report_service or UnifiedReportService(settings=self.settings)
        self.formatter = formatter or AlertFormatter()
        self.console_channel = console_channel or ConsoleAlertChannel()
        self.discord_channel = discord_channel or DiscordDryRunChannel(settings=self.settings)

    def build_alert_report(self) -> AlertReport:
        """Build an alert report from read-only summaries."""
        top = self._safe(lambda: self.unified_report_service.get_top_candidates(), {"crypto": [], "stocks": [], "options": []})
        health = self._safe(lambda: self.unified_report_service.get_system_health_summary(), {"risk": {}, "safety": {"passed": False}})
        warnings: list[str] = []
        if not self.settings.alerts_enabled:
            warnings.append("Alerts disabled; preview only")
        if not top.get("crypto") and not top.get("stocks") and not top.get("options"):
            warnings.append("No alert candidates met thresholds")
        return AlertReport(
            title="YucaTanaTrades Candidate Alert",
            crypto_candidates=top.get("crypto", []),
            stock_candidates=top.get("stocks", []),
            option_candidates=top.get("options", []),
            risk_summary=health.get("risk", {}) if self.settings.alert_include_risk_status else {},
            safety_summary=health.get("safety", {}) if self.settings.alert_include_safety_status else {},
            warnings=warnings,
        )

    def preview_alert_report(self) -> dict:
        """Return report plus formatted previews."""
        report = self.build_alert_report()
        return {
            "report": report.to_dict(),
            "markdown": self.formatter.format_markdown_report(report),
            "console": self.formatter.format_console_report(report),
            "compact": self.formatter.format_compact_summary(report),
            "source": "yucatanatrades_alert_preview_v1",
        }

    def send_console_alert(self) -> dict:
        """Send or block a console alert according to safe settings."""
        report = self.build_alert_report()
        message = self.formatter.format_console_report(report)
        if not self.settings.alerts_enabled:
            return self.console_channel.send(message, enabled=False)
        return self.console_channel.send(message, enabled=self.settings.alert_channel_console)

    def send_discord_alert_dry_run(self) -> dict:
        """Preview Discord sending without calling a webhook."""
        report = self.build_alert_report()
        message = self.formatter.format_markdown_report(report)
        return self.discord_channel.dry_run(message).to_dict()

    def get_alert_status(self) -> dict:
        """Return alert status without exposing webhook URLs."""
        return {
            "enabled": self.settings.alerts_enabled,
            "read_only": self.settings.alerts_read_only,
            "channels": {
                "console": self.settings.alert_channel_console,
                "discord": self.settings.alert_channel_discord,
                "email": False,
            },
            "thresholds": {
                "crypto": self.settings.alert_min_crypto_score,
                "stock": self.settings.alert_min_stock_score,
                "options": self.settings.alert_min_options_score,
            },
            "discord_webhook_configured": bool(self.settings.discord_webhook_url),
            "source": "yucatanatrades_alert_status_v1",
        }

    def _safe(self, fn, default):
        """Return default if optional data is unavailable."""
        try:
            return fn()
        except Exception:
            return default
