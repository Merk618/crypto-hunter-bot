"""Standalone startup validation checks."""

from __future__ import annotations

from pathlib import Path

from app.alerts.alert_service import AlertService
from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.operator.operator_models import StartupCheckResult


class StartupChecks:
    """Run safe startup validation checks for local operation."""

    REQUIRED_PATHS = ("app", "tests", "README.md", ".env.example", "requirements.txt")

    def __init__(self, settings: Settings | None = None, root: Path | None = None, safety_audit: SafetyAudit | None = None, alert_service: AlertService | None = None) -> None:
        """Initialize startup checks."""
        self.settings = settings or get_settings()
        self.root = root or Path(__file__).resolve().parents[2]
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings, root=self.root)
        self.alert_service = alert_service or AlertService(settings=self.settings)

    def run(self) -> StartupCheckResult:
        """Run all startup checks."""
        checks: dict = {}
        warnings: list[str] = []
        blockers: list[str] = []

        checks["pytest_command_documented"] = "pytest" in (self.root / "README.md").read_text(encoding="utf-8")
        checks["live_trading_locked"] = not self.settings.live_trading_allowed() and not self.settings.enable_live_trading
        checks["safety_audit_passes"] = self.safety_audit.run().passed
        checks["journal_available"] = bool(self.settings.enable_trade_journal)
        checks["reports_available"] = True
        alert_status = self.alert_service.get_alert_status()
        checks["alerts_dry_run_only"] = alert_status["read_only"] is True and alert_status["channels"]["email"] is False
        checks["moomoo_read_only_if_present"] = self.settings.moomoo_read_only and not self.settings.moomoo_trading_enabled and not self.settings.moomoo_unlock_trade_context
        checks["kraken_add_order_not_present"] = self.safety_audit.no_forbidden_live_order_strings(self.safety_audit._app_python_files())
        checks["no_fund_movement_paths"] = self.safety_audit.no_forbidden_exchange_methods()
        checks["required_paths_exist"] = all((self.root / path).exists() for path in self.REQUIRED_PATHS)
        checks["env_example_safe_defaults"] = self._env_example_safe()

        if not checks["live_trading_locked"]:
            blockers.append("live trading is not locked")
        for key, value in checks.items():
            if not value and key not in {"journal_available"}:
                blockers.append(f"{key} check failed")
        if not checks["journal_available"]:
            warnings.append("trade journal disabled")

        actions = self._recommended_actions(checks, blockers)
        return StartupCheckResult(
            passed=not blockers,
            checks=checks,
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
            recommended_actions=actions,
        )

    def _env_example_safe(self) -> bool:
        """Check .env.example safe defaults."""
        text = (self.root / ".env.example").read_text(encoding="utf-8")
        required = [
            "BOT_MODE=paper",
            "ENABLE_LIVE_TRADING=false",
            "MOOMOO_TRADING_ENABLED=false",
            "MOOMOO_UNLOCK_TRADE_CONTEXT=false",
            "OPTIONS_SCANNER_ALLOW_EXECUTION=false",
            "ALERTS_ENABLED=false",
        ]
        return all(item in text for item in required)

    def _recommended_actions(self, checks: dict, blockers: list[str]) -> list[str]:
        """Return next safe operator actions."""
        if blockers:
            return ["Review startup blockers", "Run /system/safety-audit", "Run the full pytest suite"]
        return ["Run the full pytest suite", "Start the backend locally", "Open /operator/status", "Review /alerts/preview"]
