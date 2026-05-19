"""Final standalone safety review."""

from __future__ import annotations

from pathlib import Path

from app.audit.standalone_readiness_models import FinalSafetyReviewReport
from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit


class FinalSafetyReview:
    """Run final read-only safety checks for Crypto Hunter v1."""

    def __init__(self, settings: Settings | None = None, safety_audit: SafetyAudit | None = None, root: Path | None = None) -> None:
        """Initialize final safety review."""
        self.settings = settings or get_settings()
        self.root = root or Path(__file__).resolve().parents[2]
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings, root=self.root)

    def review(self, safety_report: dict | None = None, executable_text: str | None = None, route_text: str | None = None) -> dict:
        """Return final safety review report."""
        safety = safety_report or self.safety_audit.run().to_dict()
        text = executable_text if executable_text is not None else self._read_python(["app", "scripts"])
        moomoo_text = executable_text if executable_text is not None else self._read_python(["app/connectors/moomoo"])
        routes = route_text if route_text is not None else self._read_file("app/api/routes.py")
        private_tokens = ("place_" + "live_" + "order", "send_" + "live_" + "order")
        private_order_absent = not any(token in text.lower() for token in private_tokens)
        def_prefix = "de" + "f "
        movement_tokens = [f"{def_prefix}{part}" for part in ("with" + "draw", "trans" + "fer", "fund" + "ing", "stak" + "ing")]
        moomoo_tokens = (def_prefix + "place_" + "order", def_prefix + "cancel_" + "order", def_prefix + "unlock_" + "trade")
        withdrawal_absent = not any(token in text.lower() for token in movement_tokens)
        moomoo_execution_absent = not any(token in moomoo_text.lower() for token in moomoo_tokens)
        real_routes_absent = "/live" not in routes.lower() and "livebroker" not in routes.lower()
        paper_labels = "CONTROLLED_PAPER_OBSERVATION" in text or "controlled paper" in text.lower()
        dangerous = bool(safety.get("dangerous_config_detected") or self.settings.enable_live_trading or self.settings.controlled_paper_observation_enabled)
        blockers = []
        if not safety.get("live_trading_locked"):
            blockers.append("Live trading lock is not confirmed.")
        if not safety.get("no_add_order_detected"):
            blockers.append("Forbidden live order token detected.")
        if not private_order_absent or not real_routes_absent:
            blockers.append("Real execution surface detected.")
        if not withdrawal_absent:
            blockers.append("Withdrawal, transfer, funding, or staking method detected.")
        if not moomoo_execution_absent:
            blockers.append("MooMoo execution method detected.")
        if not safety.get("secrets_not_exposed"):
            blockers.append("Secret scrubbing or route exposure check failed.")
        if dangerous:
            blockers.append("Dangerous config detected.")
        report = FinalSafetyReviewReport(
            passed=not blockers,
            live_trading_locked=bool(safety.get("live_trading_locked")),
            add_order_absent=bool(safety.get("no_add_order_detected")),
            private_order_methods_absent=private_order_absent and real_routes_absent,
            withdrawal_methods_absent=withdrawal_absent,
            moomoo_execution_absent=moomoo_execution_absent,
            paper_only_paths_labeled=paper_labels,
            secrets_not_exposed=bool(safety.get("secrets_not_exposed")),
            dangerous_config_detected=dangerous,
            warnings=["Crypto Hunter v1 remains observation/safety-first and does not enable live trading."],
            blockers=list(dict.fromkeys(blockers)),
        )
        return report.to_dict()

    def _read_python(self, paths: list[str]) -> str:
        """Read Python files for synthetic-safe scanning."""
        chunks = []
        for rel in paths:
            path = self.root / rel
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8"))
            elif path.exists():
                for file_path in path.rglob("*.py"):
                    if "__pycache__" not in file_path.parts:
                        chunks.append(file_path.read_text(encoding="utf-8"))
        return "\n".join(chunks)

    def _read_file(self, rel: str) -> str:
        """Read a repo file."""
        path = self.root / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
