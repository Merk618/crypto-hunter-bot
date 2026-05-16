"""Paper-observation readiness checks."""

from __future__ import annotations

from app.alerts.alert_service import AlertService
from app.core.safety_audit import SafetyAudit
from app.execution.paper_broker import PaperBroker
from app.journal.journal_hygiene import JournalHygiene
from app.observation.observation_models import ObservationReadinessResult
from app.operator.operator_service import OperatorService
from app.reporting.unified_report_service import UnifiedReportService
from app.storage.trade_journal import TradeJournal
from app.validation.real_data_validator import RealDataValidator


class ObservationReadinessChecker:
    """Validate readiness for long-running paper observation mode."""

    def __init__(
        self,
        safety_audit: SafetyAudit | None = None,
        validator: RealDataValidator | None = None,
        paper_broker: PaperBroker | None = None,
        trade_journal: TradeJournal | None = None,
        report_service: UnifiedReportService | None = None,
        operator_service: OperatorService | None = None,
        alert_service: AlertService | None = None,
        journal_hygiene: JournalHygiene | None = None,
    ) -> None:
        """Initialize readiness dependencies."""
        self.safety_audit = safety_audit or SafetyAudit()
        self.validator = validator or RealDataValidator()
        self.paper_broker = paper_broker or PaperBroker()
        self.trade_journal = trade_journal or TradeJournal()
        self.report_service = report_service or UnifiedReportService()
        self.operator_service = operator_service or OperatorService()
        self.alert_service = alert_service or AlertService()
        self.journal_hygiene = journal_hygiene or JournalHygiene(self.trade_journal)

    def check(self) -> dict:
        """Run read-only readiness checks."""
        checks: dict = {}
        warnings: list[str] = []
        blockers: list[str] = []

        safety = self._safe(lambda: self.safety_audit.run().to_dict(), {"passed": False, "live_trading_locked": False, "blockers": ["safety audit unavailable"]})
        checks["safety_audit_passes"] = bool(safety.get("passed"))
        checks["live_trading_locked"] = bool(safety.get("live_trading_locked"))
        blockers.extend(safety.get("blockers") or [])

        kraken = self._safe(lambda: self.validator.validate_kraken_public_data().to_dict(), {"passed": False, "blockers": ["Kraken validation unavailable"]})
        crypto = self._safe(lambda: self.validator.validate_crypto_signals().to_dict(), {"passed": False, "blockers": ["Crypto signal validation unavailable"]})
        checks["kraken_public_data_works"] = bool(kraken.get("passed"))
        checks["crypto_signal_generation_works"] = bool(crypto.get("passed"))
        blockers.extend(kraken.get("blockers") or [])
        blockers.extend(crypto.get("blockers") or [])

        account = self._safe(lambda: self.paper_broker.get_account_summary(), {})
        checks["paper_account_available"] = bool(account)
        if not account:
            blockers.append("paper account unavailable")

        checks["journal_available"] = self._safe(lambda: isinstance(self.trade_journal.get_recent_signals(limit=1), list), False)
        if not checks["journal_available"]:
            blockers.append("journal unavailable")

        briefing = self._safe(lambda: self.report_service.get_daily_briefing(), {"top_candidates": {"crypto": [], "stocks": [], "options": []}})
        polluted = self._briefing_polluted(briefing)
        checks["reports_not_polluted_with_test_data"] = not polluted
        if polluted:
            blockers.append("daily briefing contains fake/test/demo records")

        operator = self._safe(lambda: self.operator_service.get_operator_status(), {})
        checks["operator_layer_available"] = bool(operator)
        if not operator:
            blockers.append("operator layer unavailable")

        alerts = self._safe(lambda: self.alert_service.get_alert_status(), {})
        checks["alerts_dry_run_read_only"] = bool(alerts.get("read_only", True)) and alerts.get("channels", {}).get("email") is False
        if not checks["alerts_dry_run_read_only"]:
            blockers.append("alerts are not read-only/dry-run")

        checks["no_real_execution_paths"] = bool(safety.get("no_add_order_detected", True) and safety.get("no_withdrawal_methods_detected", True))
        if not checks["no_real_execution_paths"]:
            blockers.append("real execution path detected")

        moomoo = self._safe(lambda: self.validator.validate_moomoo_health().to_dict(), {"status": "unavailable", "warnings": ["MooMoo unavailable"]})
        if moomoo.get("status") in {"disabled", "disconnected", "failed"}:
            warnings.extend(moomoo.get("warnings") or ["MooMoo disabled; crypto-only observation can continue"])

        ready = not blockers and all(checks.values())
        actions = self._actions(blockers, warnings)
        return ObservationReadinessResult(ready, checks, list(dict.fromkeys(warnings)), list(dict.fromkeys(blockers)), actions).to_dict()

    def _briefing_polluted(self, briefing: dict) -> bool:
        """Return True if daily briefing still contains test/demo records."""
        top = briefing.get("top_candidates", {})
        for section in ("crypto", "stocks", "options"):
            records = top.get(section, [])
            if self.journal_hygiene.detect_test_records_from(records):
                return True
        return False

    def _actions(self, blockers: list[str], warnings: list[str]) -> list[str]:
        """Build recommended actions."""
        if blockers:
            return ["Review /observation/readiness blockers", "Run /validation/run", "Run /journal/hygiene/summary"]
        actions = ["Start with short paper observation windows", "Review /reports/daily-briefing before and after observation"]
        if warnings:
            actions.append("Review warnings before relying on stock/options sections")
        return actions

    def _safe(self, fn, default):
        """Return default if a check is unavailable."""
        try:
            return fn()
        except Exception:
            return default
