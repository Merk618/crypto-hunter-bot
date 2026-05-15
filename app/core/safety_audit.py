"""Safety audit checks for Crypto Hunter."""

from __future__ import annotations

import inspect
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.config import Settings
from app.execution.dry_run_executor import DryRunExecutor
from app.execution.execution_guard import ExecutionGuard
from app.execution.live_broker import LiveBroker, LiveTradingDisabledError
from app.execution.order_validator import OrderValidator
from app.exchanges.kraken_adapter import KrakenAdapter
from app.exchanges.kraken_private_client import KrakenPrivateClient
from app.storage.serializers import scrub_secrets


@dataclass
class SafetyAuditReport:
    """Structured safety audit result."""

    passed: bool
    checked_at: str
    blockers: list[str]
    warnings: list[str]
    checks: dict
    live_trading_locked: bool
    no_add_order_detected: bool
    no_withdrawal_methods_detected: bool
    secrets_not_exposed: bool
    dangerous_config_detected: bool
    source: str = "crypto_hunter_safety_audit_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly report."""
        return asdict(self)


class SafetyAudit:
    """Run read-only safety and integration hardening checks."""

    FORBIDDEN_PRIVATE_METHOD_PARTS = ("withdraw", "transfer", "funding", "staking")

    def __init__(self, settings: Settings | None = None, root: Path | None = None) -> None:
        """Initialize audit with settings and repository root."""
        self.settings = settings or Settings(_env_file=None)
        self.root = root or Path(__file__).resolve().parents[2]

    def run(self) -> SafetyAuditReport:
        """Run the full safety audit."""
        blockers: list[str] = []
        warnings: list[str] = []
        checks: dict = {}

        dangerous_config = self._check_config(blockers, checks)
        live_locked = self._check_live_guard(blockers, checks)
        add_order_clean = self.no_forbidden_live_order_strings(self._app_python_files())
        checks["no_forbidden_live_order_strings"] = add_order_clean
        if not add_order_clean:
            blockers.append("forbidden Kraken live order string detected in executable code")

        no_withdrawals = self.no_forbidden_exchange_methods()
        checks["no_forbidden_exchange_methods"] = no_withdrawals
        if not no_withdrawals:
            blockers.append("forbidden withdrawal, transfer, funding, or staking method detected")

        secrets_clean = self._check_secret_scrubbing()
        checks["journal_serializers_scrub_secrets"] = secrets_clean
        if not secrets_clean:
            blockers.append("secret-like fields are not scrubbed")

        checks["order_validator_has_no_live_broker"] = not hasattr(OrderValidator(self.settings), "live_broker")
        checks["dry_run_executor_has_no_live_broker"] = not hasattr(DryRunExecutor(self.settings), "live_broker")
        checks["private_account_disabled_by_default"] = Settings(_env_file=None).kraken_private_read_enabled is False
        checks["paper_auto_trading_only"] = self.settings.paper_allow_autobuy is True and self.settings.paper_allow_autosell is False
        checks["fastapi_routes_do_not_expose_secrets"] = self._routes_do_not_expose_secrets()
        checks["no_real_exchange_order_route_detected"] = self._routes_do_not_expose_live_order()

        for key in [
            "order_validator_has_no_live_broker",
            "dry_run_executor_has_no_live_broker",
            "private_account_disabled_by_default",
            "fastapi_routes_do_not_expose_secrets",
            "no_real_exchange_order_route_detected",
        ]:
            if not checks[key]:
                blockers.append(f"{key} check failed")

        passed = not blockers
        return SafetyAuditReport(
            passed=passed,
            checked_at=datetime.now(timezone.utc).isoformat(),
            blockers=list(dict.fromkeys(blockers)),
            warnings=warnings,
            checks=checks,
            live_trading_locked=live_locked,
            no_add_order_detected=add_order_clean,
            no_withdrawal_methods_detected=no_withdrawals,
            secrets_not_exposed=secrets_clean,
            dangerous_config_detected=dangerous_config,
        )

    def no_forbidden_live_order_strings(self, paths: Iterable[Path]) -> bool:
        """Return False if Kraken live order strings appear in executable code."""
        forbidden = ("Add" + "Order",)
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for token in forbidden:
                if token in text:
                    return False
        return True

    def no_forbidden_exchange_methods(self) -> bool:
        """Return True when exchange clients expose no forbidden movement methods."""
        clients = [KrakenAdapter, KrakenPrivateClient]
        names = " ".join(name.lower() for client in clients for name, _ in inspect.getmembers(client))
        return not any(part in names for part in self.FORBIDDEN_PRIVATE_METHOD_PARTS)

    def _check_config(self, blockers: list[str], checks: dict) -> bool:
        """Check default and current dangerous config flags."""
        defaults = Settings(_env_file=None)
        checks["default_live_trading_gate_enabled_false"] = defaults.live_trading_gate_enabled is False
        checks["default_enable_live_trading_false"] = defaults.enable_live_trading is False
        checks["default_private_trading_false"] = defaults.kraken_private_trading_enabled is False
        checks["default_dry_run_enabled_true"] = defaults.dry_run_execution_enabled is True
        current_dangerous = bool(
            self.settings.live_trading_gate_enabled
            or self.settings.enable_live_trading
            or self.settings.kraken_private_trading_enabled
            or not self.settings.dry_run_execution_enabled
        )
        checks["dangerous_config_detected"] = current_dangerous
        for key in [
            "default_live_trading_gate_enabled_false",
            "default_enable_live_trading_false",
            "default_private_trading_false",
            "default_dry_run_enabled_true",
        ]:
            if not checks[key]:
                blockers.append(f"{key} check failed")
        if current_dangerous:
            blockers.append("dangerous live-trading configuration detected")
        return current_dangerous

    def _check_live_guard(self, blockers: list[str], checks: dict) -> bool:
        """Check guard and broker refusal behavior."""
        guard = ExecutionGuard(self.settings)
        checks["execution_guard_blocks_live"] = guard.can_execute_live_order() is False
        try:
            LiveBroker(KrakenAdapter(settings=self.settings), settings=Settings(_env_file=None)).place_order("BTC/USD", "buy", "market", 0.001)
            live_broker_refuses = False
        except LiveTradingDisabledError:
            live_broker_refuses = True
        checks["live_broker_refuses_orders"] = live_broker_refuses
        if not checks["execution_guard_blocks_live"]:
            blockers.append("execution guard permits live order execution")
        if not live_broker_refuses:
            blockers.append("live broker did not refuse an order under default config")
        return checks["execution_guard_blocks_live"] and live_broker_refuses

    def _check_secret_scrubbing(self) -> bool:
        """Check journal serializer secret scrubbing."""
        sample = {"api_key": "key", "nested": {"token": "tok", "safe": "ok"}}
        scrubbed = scrub_secrets(sample)
        return "api_key" not in scrubbed and "token" not in scrubbed.get("nested", {}) and scrubbed["nested"]["safe"] == "ok"

    def _routes_do_not_expose_secrets(self) -> bool:
        """Check route declarations for secret-bearing paths."""
        route_file = self.root / "app" / "api" / "routes.py"
        text = route_file.read_text(encoding="utf-8").lower()
        return "api_key" not in text and "api-secret" not in text and "/secrets" not in text

    def _routes_do_not_expose_live_order(self) -> bool:
        """Check route declarations for real live-order surfaces."""
        route_file = self.root / "app" / "api" / "routes.py"
        text = route_file.read_text(encoding="utf-8").lower()
        return "/live" not in text and ("add" + "order").lower() not in text and "livebroker" not in text

    def _app_python_files(self) -> list[Path]:
        """Return executable app Python files to scan."""
        return [path for path in (self.root / "app").rglob("*.py") if "__pycache__" not in path.parts]
