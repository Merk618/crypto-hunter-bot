"""Unified read-only reports across Crypto, Stock, and Options Hunter."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit
from app.journal.journal_filters import dedupe_candidates, filter_production_records
from app.observation.early_recovery_watchlist import EarlyRecoveryWatchlistService
from app.reporting.candidate_summary import candidate_from_crypto_signal, candidate_from_early_recovery, candidate_from_ranked_option, candidate_from_stock_result
from app.reporting.dashboard_service import DashboardService
from app.stock_hunter.stock_hunter_service import StockHunterService


class UnifiedReportService:
    """Aggregate read-only summaries for the future YucaTanaTrades frontend."""

    def __init__(
        self,
        settings: Settings | None = None,
        dashboard_service: DashboardService | None = None,
        stock_service: StockHunterService | None = None,
        safety_audit: SafetyAudit | None = None,
    ) -> None:
        """Initialize report dependencies."""
        self.settings = settings or get_settings()
        self.dashboard_service = dashboard_service or DashboardService()
        self.stock_service = stock_service or StockHunterService(settings=self.settings)
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)

    def get_unified_dashboard_summary(self) -> dict:
        """Return one compact read-only dashboard summary."""
        return {
            "overview": self._safe(lambda: self.dashboard_service.get_overview().to_dict(), {}),
            "top_candidates": self.get_top_candidates(),
            "risk_safety": self.get_system_health_summary(),
            "generated_at": self._now(),
            "source": "yucatanatrades_unified_summary_v1",
        }

    def get_top_candidates(self) -> dict:
        """Return normalized top candidates across asset classes."""
        crypto = self._crypto_candidates()
        early_recovery = self._early_recovery_candidates()
        stock = self._stock_candidates()
        options = self._option_candidates()
        return {
            "crypto": dedupe_candidates([candidate.to_dict() for candidate in crypto]),
            "early_recovery": dedupe_candidates([candidate.to_dict() for candidate in early_recovery]),
            "stocks": dedupe_candidates([candidate.to_dict() for candidate in stock]),
            "options": dedupe_candidates([candidate.to_dict() for candidate in options]),
            "generated_at": self._now(),
            "source": "yucatanatrades_top_candidates_v1",
        }

    def get_daily_briefing(self) -> dict:
        """Return a daily briefing-ready summary."""
        top = self.get_top_candidates()
        health = self.get_system_health_summary()
        return {
            "title": "YucaTanaTrades Daily Briefing",
            "top_candidates": top,
            "system_health": health,
            "warnings": self._briefing_warnings(top, health),
            "generated_at": self._now(),
            "source": "yucatanatrades_daily_briefing_v1",
        }

    def get_system_health_summary(self) -> dict:
        """Return risk and safety summary without secrets."""
        risk = self._safe(lambda: self.dashboard_service.get_risk_summary().to_dict(), {})
        safety = self._safe(lambda: self.safety_audit.run().to_dict(), {"passed": False, "warnings": ["safety audit unavailable"]})
        return {
            "risk": risk,
            "safety": {
                "passed": bool(safety.get("passed", False)),
                "live_trading_locked": bool(safety.get("live_trading_locked", True)),
                "no_add_order_detected": bool(safety.get("no_add_order_detected", True)),
                "no_withdrawal_methods_detected": bool(safety.get("no_withdrawal_methods_detected", True)),
                "blockers": safety.get("blockers", []),
                "warnings": safety.get("warnings", []),
            },
            "generated_at": self._now(),
            "source": "yucatanatrades_system_health_v1",
        }

    def _crypto_candidates(self) -> list:
        """Read recent crypto signal records from the journal."""
        report = self._safe(lambda: self.dashboard_service.get_signal_performance(limit=100).to_dict(), {"recent_signals": []})
        records = filter_production_records(report.get("recent_signals", []))
        candidates = [candidate_from_crypto_signal(signal) for signal in records]
        filtered = [candidate for candidate in candidates if candidate.score >= self.settings.alert_min_crypto_score]
        return sorted(filtered, key=lambda item: item.score, reverse=True)[: self.settings.alert_max_items_per_section]

    def _stock_candidates(self) -> list:
        """Read Stock Hunter top candidates."""
        response = self._safe(lambda: self.stock_service.top_candidates(limit=self.settings.alert_max_items_per_section), {"results": []})
        records = filter_production_records(response.get("results", []))
        candidates = [candidate_from_stock_result(result) for result in records]
        filtered = [candidate for candidate in candidates if candidate.score >= self.settings.alert_min_stock_score]
        return sorted(filtered, key=lambda item: item.score, reverse=True)[: self.settings.alert_max_items_per_section]

    def _option_candidates(self) -> list:
        """Read Options Scanner top candidates."""
        response = self._safe(lambda: self.stock_service.top_options(limit=self.settings.alert_max_items_per_section), {"top_candidates": []})
        records = filter_production_records(response.get("top_candidates", []))
        candidates = [candidate_from_ranked_option(contract) for contract in records]
        filtered = [candidate for candidate in candidates if candidate.score >= self.settings.alert_min_options_score]
        return sorted(filtered, key=lambda item: item.score, reverse=True)[: self.settings.alert_max_items_per_section]

    def _early_recovery_candidates(self) -> list:
        """Read observation-only early recovery candidates."""
        response = self._safe(lambda: EarlyRecoveryWatchlistService(settings=self.settings).get_report(), {"candidates": []})
        records = filter_production_records(response.get("candidates", []))
        candidates = [candidate_from_early_recovery(item) for item in records]
        return sorted(candidates, key=lambda item: item.score, reverse=True)[: self.settings.alert_max_items_per_section]

    def _briefing_warnings(self, top: dict, health: dict) -> list[str]:
        """Create briefing warnings."""
        warnings: list[str] = []
        if not top.get("crypto") and not top.get("early_recovery") and not top.get("stocks") and not top.get("options"):
            warnings.append("No candidates met alert thresholds")
        if not health.get("safety", {}).get("passed", False):
            warnings.append("Safety audit is not passing")
        return warnings

    def _safe(self, fn, default):
        """Return default when optional data is unavailable."""
        try:
            return fn()
        except Exception:
            return default

    def _now(self) -> str:
        """Return UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()
