"""Controlled paper observation guardrail audit."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.observation.controlled_paper_review import ControlledPaperReviewService


@dataclass
class ControlledPaperAuditCheck:
    """One controlled paper audit check."""

    name: str
    passed: bool
    status: str
    message: str
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ControlledPaperAuditReport:
    """Controlled paper audit report."""

    passed: bool
    generated_at: str
    controlled_paper_enabled: bool
    buys_allowed: bool
    sells_allowed: bool
    live_trades_detected: int
    real_execution_detected: int
    non_paper_broker_detected: int
    preview_created_trades: int
    disabled_run_created_trades: int
    paper_only_labels_valid: bool
    checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    source: str = "crypto_hunter_controlled_paper_audit_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class ControlledPaperAuditService:
    """Read-only controlled paper guardrail auditor."""

    def __init__(self, settings: Settings | None = None, runs: list[dict] | None = None) -> None:
        """Initialize audit service."""
        self.settings = settings or get_settings()
        self.runs = runs or []

    def audit(self, runs: list[dict] | None = None) -> dict:
        """Return controlled paper guardrail audit."""
        records = runs if runs is not None else self.runs
        review = ControlledPaperReviewService(settings=self.settings, runs=records).review()
        live = self._count(records, "live_trade", True)
        real = self._count(records, "real_execution", True)
        non_paper = self._non_paper_brokers(records)
        preview_trades = sum(1 for run in records if int(run.get("paper_trade_previews_created", 0) or 0) > 0 and int(run.get("paper_trades_created", 0) or 0) > 0 and run.get("status") == "PREVIEW_ONLY")
        disabled_trades = sum(1 for run in records if run.get("status") == "DISABLED_BY_CONFIG" and int(run.get("paper_trades_created", 0) or 0) > 0)
        checks = [
            self._check("disabled_by_default", not self.settings.controlled_paper_observation_enabled, "Controlled paper observation must be disabled by default"),
            self._check("buys_disabled_by_default", not self.settings.controlled_paper_observation_allow_buys, "Controlled paper buys must be disabled by default"),
            self._check("sells_disabled", not self.settings.controlled_paper_observation_allow_sells, "Controlled paper sells must remain disabled"),
            self._check("zero_live_trades", live == 0, "No controlled paper records may be live trades", {"live_trades_detected": live}),
            self._check("real_execution_false", real == 0, "No controlled paper records may have real_execution=true", {"real_execution_detected": real}),
            self._check("paper_broker_only", non_paper == 0, "Controlled paper records must use broker=PAPER", {"non_paper_broker_detected": non_paper}),
            self._check("preview_no_trades", preview_trades == 0, "Preview-only records must create zero paper trades", {"preview_created_trades": preview_trades}),
            self._check("disabled_run_no_trades", disabled_trades == 0, "Disabled run-once records must create zero paper trades", {"disabled_run_created_trades": disabled_trades}),
            self._check("paper_only_labels_valid", bool(review.get("paper_only_labels_valid")), "Controlled paper labels must be paper-only"),
        ]
        blockers = [blocker for check in checks for blocker in check.blockers]
        warnings = ["Controlled paper observation is disabled by default."] if not self.settings.controlled_paper_observation_enabled else []
        return ControlledPaperAuditReport(
            passed=not blockers,
            generated_at=datetime.now(timezone.utc).isoformat(),
            controlled_paper_enabled=self.settings.controlled_paper_observation_enabled,
            buys_allowed=self.settings.controlled_paper_observation_allow_buys,
            sells_allowed=self.settings.controlled_paper_observation_allow_sells,
            live_trades_detected=live,
            real_execution_detected=real,
            non_paper_broker_detected=non_paper,
            preview_created_trades=preview_trades,
            disabled_run_created_trades=disabled_trades,
            paper_only_labels_valid=bool(review.get("paper_only_labels_valid")),
            checks=[check.to_dict() for check in checks],
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
            recommended_next_actions=self._actions(blockers),
        ).to_dict()

    def guardrails(self, runs: list[dict] | None = None) -> dict:
        """Return compact guardrail status."""
        report = self.audit(runs)
        return {
            "passed": report["passed"],
            "controlled_paper_enabled": report["controlled_paper_enabled"],
            "paper_only_labels_valid": report["paper_only_labels_valid"],
            "blockers": report["blockers"],
            "warnings": report["warnings"],
            "source": "crypto_hunter_controlled_paper_guardrails_v1",
        }

    def _check(self, name: str, passed: bool, message: str, metadata: dict | None = None) -> ControlledPaperAuditCheck:
        """Build audit check."""
        return ControlledPaperAuditCheck(
            name=name,
            passed=passed,
            status="PASS" if passed else "BLOCKED",
            message=message,
            blockers=[] if passed else [message],
            metadata=metadata or {},
        )

    def _count(self, runs: list[dict], field: str, value) -> int:
        """Count trade results matching field value."""
        return sum(1 for run in runs for trade in (run.get("trade_results", []) or []) if trade.get(field) is value)

    def _non_paper_brokers(self, runs: list[dict]) -> int:
        """Count controlled paper trade records with non-PAPER broker."""
        return sum(1 for run in runs for trade in (run.get("trade_results", []) or []) if trade.get("broker") not in {None, "PAPER"})

    def _actions(self, blockers: list[str]) -> list[str]:
        """Return audit actions."""
        if blockers:
            return ["Resolve controlled paper guardrail blockers before any future paper observation enablement."]
        return ["Guardrails pass; keep controlled paper observation disabled until operator review."]
