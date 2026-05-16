"""Safe Phase 14 smoke-test runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.config import BotMode, Settings, get_settings
from app.core.app_state import AppState
from app.core.dependencies import (
    get_dashboard_service,
    get_market_data_service,
    get_paper_trading_bot,
    get_risk_manager,
    get_strategy,
    get_trade_journal,
)
from app.core.safety_audit import SafetyAudit


@dataclass
class SmokeCheck:
    """One smoke-test check result."""

    name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return {"name": self.name, "passed": self.passed, "message": self.message, "details": self.details}


class SmokeTestRunner:
    """Run a safe local end-to-end diagnostic without live execution."""

    def __init__(
        self,
        settings: Settings | None = None,
        market_data_service=None,
        strategy=None,
        risk_manager=None,
        paper_bot=None,
        journal=None,
        dashboard_service=None,
        safety_audit: SafetyAudit | None = None,
        app_state: AppState | None = None,
    ) -> None:
        """Initialize smoke-test dependencies."""
        self.settings = settings or get_settings()
        self.market_data_service = market_data_service or get_market_data_service()
        self.strategy = strategy or get_strategy()
        self.risk_manager = risk_manager or get_risk_manager()
        self.paper_bot = paper_bot or get_paper_trading_bot()
        self.journal = journal or get_trade_journal()
        self.dashboard_service = dashboard_service or get_dashboard_service()
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.app_state = app_state or AppState(settings=self.settings)

    def run(self, symbols: list[str] | None = None, timeframe: str | None = None, limit: int | None = None, allow_paper_scan: bool | None = None) -> dict:
        """Run the smoke test and return structured pass/fail diagnostics."""
        symbols = symbols or self.settings.phase14_smoke_symbols
        timeframe = timeframe or self.settings.phase14_timeframe
        limit = limit or self.settings.phase14_candle_limit
        allow_paper_scan = self.settings.phase14_allow_paper_scan if allow_paper_scan is None else allow_paper_scan
        checks: list[SmokeCheck] = []
        warnings: list[str] = []
        blockers: list[str] = []
        signals: list[dict] = []
        symbols_checked: list[str] = []

        self._add_check(checks, "runtime_status", True, "Runtime status available", self.app_state.get_runtime_summary())
        audit_report = self.safety_audit.run()
        self._add_check(checks, "safety_audit", audit_report.passed, "Safety audit passed" if audit_report.passed else "Safety audit failed", audit_report.to_dict())
        if not audit_report.passed:
            blockers.extend(audit_report.blockers)

        live_locked = audit_report.live_trading_locked and not self.settings.enable_live_trading and self.settings.bot_mode == BotMode.PAPER
        self._add_check(checks, "live_trading_locked", live_locked, "Live trading is locked" if live_locked else "Live trading lock failed")
        if not live_locked:
            blockers.append("Live trading lock failed")

        for symbol in symbols:
            normalized = symbol.upper().replace("-", "/")
            try:
                ticker = self.market_data_service.get_symbol_ticker(normalized)
                candles = self.market_data_service.get_symbol_candles(normalized, timeframe=timeframe, limit=limit)
                signal = self.strategy.evaluate(pd.DataFrame(candles), symbol=normalized, timeframe=timeframe)
                account_summary = {"equity": 10000, "cash_balance": 10000, "realized_pnl": 0, "trades_today": 0, "consecutive_losses": 0}
                risk = self.risk_manager.evaluate_trade(
                    normalized,
                    "buy",
                    signal,
                    account_summary=account_summary,
                    open_positions=[],
                    market_price=float(signal.latest_price),
                    spread_bps=self._spread_bps(ticker),
                )
                signal_dict = signal.to_dict()
                signal_dict["risk_decision"] = risk.to_dict()
                signals.append(signal_dict)
                symbols_checked.append(normalized)
                self._add_check(
                    checks,
                    f"market_signal_{normalized}",
                    True,
                    "Market data, indicators, signal, and risk evaluation completed",
                    {"ticker": ticker, "signal_category": signal.category, "risk_approved": risk.approved},
                )
            except Exception as exc:  # noqa: BLE001 - diagnostics should keep going
                warnings.append(f"{normalized}: {exc}")
                self._add_check(checks, f"market_signal_{normalized}", False, str(exc), {"symbol": normalized})

        paper_scan_checked = False
        try:
            start_status = self.paper_bot.start(manual_start=True)
            self._add_check(checks, "paper_bot_manual_start", start_status.get("is_running") is True and start_status.get("mode") == "paper", "Paper bot manual start checked", start_status)
            if allow_paper_scan:
                scan = self.paper_bot.scan_once()
                paper_scan_checked = True
                self._add_check(checks, "paper_scan_once", True, "Paper scan completed", scan)
            else:
                self._add_check(checks, "paper_scan_once", True, "Paper scan skipped by PHASE14_ALLOW_PAPER_SCAN=false", {"skipped": True})
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"paper bot check: {exc}")
            self._add_check(checks, "paper_bot", False, str(exc))

        try:
            self.journal.record_bot_event("phase14_smoke_test", "Phase 14 smoke test executed", {"symbols": symbols_checked})
            events = self.journal.get_recent_bot_events(limit=5)
            self._add_check(checks, "journal_records", bool(events), "Journal record check completed", {"recent_events": len(events)})
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"journal check: {exc}")
            self._add_check(checks, "journal_records", False, str(exc))

        try:
            dashboard = self.dashboard_service.get_full_dashboard_snapshot()
            self._add_check(checks, "full_dashboard", isinstance(dashboard, dict), "Full dashboard read completed", {"keys": sorted(dashboard.keys())})
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"dashboard check: {exc}")
            self._add_check(checks, "full_dashboard", False, str(exc))

        passed = all(check.passed for check in checks if check.name in {"runtime_status", "safety_audit", "live_trading_locked"}) and not blockers
        return {
            "passed": passed,
            "checks": [check.to_dict() for check in checks],
            "warnings": warnings,
            "blockers": list(dict.fromkeys(blockers)),
            "symbols_checked": symbols_checked,
            "signals_generated": len(signals),
            "paper_scan_checked": paper_scan_checked,
            "live_trading_locked": live_locked,
            "safety_audit_passed": audit_report.passed,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "crypto_hunter_phase14_smoke_test",
        }

    def _add_check(self, checks: list[SmokeCheck], name: str, passed: bool, message: str, details: dict | None = None) -> None:
        """Append a smoke check."""
        checks.append(SmokeCheck(name=name, passed=passed, message=message, details=details or {}))

    def _spread_bps(self, ticker: dict) -> float | None:
        """Calculate spread bps from ticker bid/ask."""
        bid = float(ticker.get("bid") or 0)
        ask = float(ticker.get("ask") or 0)
        mid = (bid + ask) / 2
        if bid <= 0 or ask <= 0 or mid <= 0:
            return None
        return ((ask - bid) / mid) * 10000
