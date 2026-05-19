"""Crypto Hunter v1 freeze and handoff models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class V1FreezeReport:
    """Final standalone v1 freeze report."""

    v1_status: str
    test_suite_status: str
    latest_test_count_expected: int
    safety_status: str
    live_trading_enabled: bool
    paper_trading_enabled: bool
    controlled_paper_enabled: bool
    add_order_absent: bool
    real_execution_absent: bool
    observation_system_available: bool
    signal_quality_available: bool
    strategy_checkpoint_available: bool
    local_runbook_available: bool
    health_check_available: bool
    docs_available: bool
    ready_to_archive_as_v1: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_v1_freeze_report_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class V1HandoffPackage:
    """Practical handoff package for local operation."""

    project_path: str
    startup_command: str
    test_command: str
    health_check_command: str
    key_endpoints: list[str]
    safety_status: dict
    intentionally_disabled: list[str]
    do_not_change_without_review: list[str]
    resume_later: list[str]
    recommended_github_tag: str
    next_project: str
    warnings: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_v1_handoff_package_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


@dataclass
class FutureRoadmap:
    """Roadmap after Crypto Hunter standalone v1."""

    crypto_hunter_future: list[str]
    stock_trader_bot: list[str]
    yucatanatrades: list[str]
    sol_meme_hunter_future: list[str]
    next_project: str
    warnings: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_future_roadmap_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)

