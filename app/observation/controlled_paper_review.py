"""Controlled paper observation review reporting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from app.config import Settings, get_settings


@dataclass
class ControlledPaperRecentItem:
    """Normalized controlled paper recent item."""

    run_id: str | None
    status: str
    created_at: str | None
    symbols_processed: int
    signals_generated: int
    risk_decisions_generated: int
    paper_trade_previews_created: int
    paper_trades_created: int
    blocked_trades: int
    mode: str | None
    broker: str | None
    real_execution: bool
    live_trade: bool
    source: str = "crypto_hunter_controlled_paper_recent_item_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class ControlledPaperReviewReport:
    """Controlled paper review report."""

    generated_at: str
    enabled: bool
    recent_runs_count: int
    recent_previews_count: int
    paper_trades_created: int
    blocked_runs_count: int
    refused_runs_count: int
    preview_only_count: int
    latest_status: str | None
    latest_blockers: list[str] = field(default_factory=list)
    latest_warnings: list[str] = field(default_factory=list)
    paper_only_labels_valid: bool = True
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    recent_items: list[dict] = field(default_factory=list)
    source: str = "crypto_hunter_controlled_paper_review_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class ControlledPaperReviewService:
    """Read-only reviewer for controlled paper observation records."""

    def __init__(self, settings: Settings | None = None, runs: list[dict] | None = None) -> None:
        """Initialize reviewer."""
        self.settings = settings or get_settings()
        self.runs = runs or []

    def review(self, runs: list[dict] | None = None) -> dict:
        """Return controlled paper review report."""
        records = (runs if runs is not None else self.runs)[: self.settings.controlled_paper_review_history_limit]
        items = [self._item(run).to_dict() for run in records]
        latest = records[0] if records else {}
        labels_valid = self._labels_valid(records)
        warnings: list[str] = []
        if not records:
            warnings.append("No controlled paper observation runs found.")
        if not self.settings.controlled_paper_observation_enabled:
            warnings.append("Controlled paper observation is disabled by default.")
        return ControlledPaperReviewReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            enabled=self.settings.controlled_paper_observation_enabled,
            recent_runs_count=len(records),
            recent_previews_count=sum(int(run.get("paper_trade_previews_created", 0) or 0) for run in records),
            paper_trades_created=sum(int(run.get("paper_trades_created", 0) or 0) for run in records),
            blocked_runs_count=sum(1 for run in records if str(run.get("status", "")).startswith("BLOCKED")),
            refused_runs_count=sum(1 for run in records if run.get("status") in {"REFUSED", "DISABLED_BY_CONFIG"}),
            preview_only_count=sum(1 for run in records if int(run.get("paper_trade_previews_created", 0) or 0) > 0 and int(run.get("paper_trades_created", 0) or 0) == 0),
            latest_status=latest.get("status"),
            latest_blockers=list(latest.get("blockers") or []),
            latest_warnings=list(latest.get("warnings") or []),
            paper_only_labels_valid=labels_valid,
            warnings=warnings,
            blockers=[] if labels_valid else ["Controlled paper labels are invalid."],
            recommended_next_actions=self._actions(records, labels_valid),
            recent_items=items,
        ).to_dict()

    def _item(self, run: dict) -> ControlledPaperRecentItem:
        """Normalize one run item."""
        labels = self._labels(run)
        return ControlledPaperRecentItem(
            run_id=run.get("run_id"),
            status=str(run.get("status", "UNKNOWN")),
            created_at=run.get("completed_at") or run.get("started_at"),
            symbols_processed=int(run.get("symbols_processed", 0) or 0),
            signals_generated=int(run.get("signals_generated", 0) or 0),
            risk_decisions_generated=int(run.get("risk_decisions_generated", 0) or 0),
            paper_trade_previews_created=int(run.get("paper_trade_previews_created", 0) or 0),
            paper_trades_created=int(run.get("paper_trades_created", 0) or 0),
            blocked_trades=int(run.get("blocked_trades", 0) or 0),
            mode=labels.get("mode"),
            broker=labels.get("broker"),
            real_execution=bool(labels.get("real_execution", False)),
            live_trade=bool(labels.get("live_trade", False)),
        )

    def _labels_valid(self, runs: list[dict]) -> bool:
        """Return whether controlled paper trade labels are valid."""
        for run in runs:
            for trade in run.get("trade_results", []) or []:
                if trade.get("mode") != "CONTROLLED_PAPER_OBSERVATION":
                    return False
                if trade.get("broker") != "PAPER":
                    return False
                if trade.get("real_execution") is not False or trade.get("live_trade") is not False:
                    return False
        return True

    def _labels(self, run: dict) -> dict:
        """Return representative labels from first trade result."""
        trades = run.get("trade_results", []) or []
        if not trades:
            return {"mode": None, "broker": None, "real_execution": False, "live_trade": False}
        return trades[0]

    def _actions(self, records: list[dict], labels_valid: bool) -> list[str]:
        """Return recommended actions."""
        actions = ["Keep controlled paper observation disabled until operator review."]
        if not records:
            actions.append("Run preview-only checks before considering any paper observation enablement.")
        if not labels_valid:
            actions.append("Investigate controlled paper record labels before continuing.")
        return actions
