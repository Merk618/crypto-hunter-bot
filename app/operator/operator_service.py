"""Standalone operator service."""

from __future__ import annotations

from app.alerts.alert_service import AlertService
from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.core.app_state import AppState
from app.core.safety_audit import SafetyAudit
from app.execution.paper_broker import PaperBroker
from app.operator.command_summary import CommandSummaryBuilder
from app.operator.operator_models import OperatorStatus
from app.operator.startup_checks import StartupChecks
from app.reporting.unified_report_service import UnifiedReportService


class OperatorService:
    """Read-only operator facade for local standalone operation."""

    def __init__(
        self,
        settings: Settings | None = None,
        app_state: AppState | None = None,
        safety_audit: SafetyAudit | None = None,
        alert_service: AlertService | None = None,
        unified_report_service: UnifiedReportService | None = None,
        paper_broker: PaperBroker | None = None,
        moomoo_client: MooMooReadOnlyClient | None = None,
        startup_checks: StartupChecks | None = None,
        command_builder: CommandSummaryBuilder | None = None,
    ) -> None:
        """Initialize operator dependencies."""
        self.settings = settings or get_settings()
        self.app_state = app_state or AppState(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.alert_service = alert_service or AlertService(settings=self.settings)
        self.unified_report_service = unified_report_service or UnifiedReportService(settings=self.settings)
        self.paper_broker = paper_broker or PaperBroker(settings=self.settings)
        self.moomoo_client = moomoo_client or MooMooReadOnlyClient(settings=self.settings)
        self.startup_checks = startup_checks or StartupChecks(settings=self.settings, safety_audit=self.safety_audit, alert_service=self.alert_service)
        self.command_builder = command_builder or CommandSummaryBuilder()

    def get_operator_status(self) -> dict:
        """Return standalone operator status."""
        safety = self._safe(lambda: self.safety_audit.run().to_dict(), {"passed": False, "live_trading_locked": False, "blockers": ["safety audit unavailable"], "warnings": []})
        account = self._safe(lambda: self.paper_broker.get_account_summary(), {})
        alerts = self._safe(lambda: self.alert_service.get_alert_status(), {})
        moomoo = self._safe(lambda: self.moomoo_client.get_health().to_dict(), {"enabled": False, "connected": False, "read_only": True})
        blockers = list(safety.get("blockers") or [])
        warnings = list(safety.get("warnings") or [])
        status = OperatorStatus(
            mode=str(self.settings.bot_mode.value),
            backend_healthy=not blockers,
            live_trading_locked=bool(safety.get("live_trading_locked", False)),
            kraken_status={"public_data": "not_checked", "reason": "operator status avoids network calls by default"},
            moomoo_status=moomoo,
            paper_status={"mode": "paper", "safe": True, "account": account},
            journal_status={"enabled": self.settings.enable_trade_journal},
            alerts_status=alerts,
            safety_audit_passed=bool(safety.get("passed", False)),
            warnings=warnings,
            blockers=blockers,
        )
        return status.to_dict()

    def run_startup_checks(self) -> dict:
        """Run startup checks."""
        return self.startup_checks.run().to_dict()

    def get_safe_command_summary(self) -> dict:
        """Return safe local commands."""
        return self.command_builder.build().to_dict()

    def get_daily_operator_briefing(self) -> dict:
        """Return daily operator briefing."""
        briefing = self._safe(lambda: self.unified_report_service.get_daily_briefing(), {"warnings": ["daily briefing unavailable"]})
        return {
            "operator_status": self.get_operator_status(),
            "daily_briefing": briefing,
            "next_actions": self.get_next_recommended_actions(),
            "source": "crypto_hunter_operator_daily_briefing_v1",
        }

    def get_next_recommended_actions(self) -> list[str]:
        """Return next recommended safe actions."""
        startup = self._safe(lambda: self.startup_checks.run().to_dict(), {"recommended_actions": ["Run startup checks"]})
        return list(startup.get("recommended_actions") or ["Run /operator/startup-checks"])

    def _safe(self, fn, default):
        """Return default when optional data is unavailable."""
        try:
            return fn()
        except Exception:
            return default
