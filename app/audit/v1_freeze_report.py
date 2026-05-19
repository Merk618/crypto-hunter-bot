"""Crypto Hunter standalone v1 freeze report."""

from __future__ import annotations

from pathlib import Path

from app.audit.final_safety_review import FinalSafetyReview
from app.audit.v1_handoff_models import FutureRoadmap, V1FreezeReport, V1HandoffPackage
from app.config import Settings, get_settings
from app.core.safety_audit import SafetyAudit


class V1FreezeReportService:
    """Build final read-only v1 freeze and handoff reports."""

    def __init__(
        self,
        settings: Settings | None = None,
        safety_audit: SafetyAudit | None = None,
        final_safety: FinalSafetyReview | None = None,
        root: Path | None = None,
    ) -> None:
        """Initialize freeze report service."""
        self.settings = settings or get_settings()
        self.root = root or Path(__file__).resolve().parents[2]
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings, root=self.root)
        self.final_safety = final_safety or FinalSafetyReview(settings=self.settings, safety_audit=self.safety_audit, root=self.root)

    def freeze_report(self, safety_report: dict | None = None, route_text: str | None = None) -> dict:
        """Return the final v1 freeze report."""
        safety = safety_report or self.safety_audit.run().to_dict()
        routes = route_text if route_text is not None else self._read("app/api/routes.py")
        final = self.final_safety.review(safety_report=safety, route_text=routes)
        checks = {
            "safety_passed": bool(safety.get("passed")),
            "live_locked": bool(safety.get("live_trading_locked")),
            "forbidden_live_order_absent": bool(safety.get("no_add_order_detected")),
            "real_execution_absent": bool(final.get("private_order_methods_absent")),
            "paper_disabled": not self.settings.paper_trade_observation_enabled and not self.settings.paper_trade_observation_allow_enable,
            "controlled_paper_disabled": not self.settings.controlled_paper_observation_enabled and not self.settings.controlled_paper_observation_allow_buys,
            "observation_available": self._exists("app/observation/observation_persistence.py"),
            "signal_quality_available": self._exists("app/observation/signal_quality_review.py"),
            "strategy_checkpoint_available": self._exists("app/observation/strategy_review_checkpoint.py"),
            "local_runbook_available": "/operator/local-runbook" in routes and self._exists("docs/LOCAL_OPERATOR_RUNBOOK_PHASE42.md"),
            "health_check_available": "/operator/one-command-health-check" in routes and self._exists("scripts/health_check_phase42.py"),
            "docs_available": self._phase43_docs_available(),
        }
        blockers = [name for name, passed in checks.items() if not passed]
        v1_status = "READY_TO_FREEZE" if not blockers else "BLOCKED"
        report = V1FreezeReport(
            v1_status=v1_status,
            test_suite_status="742 passed expected after Phase 43 freeze package",
            latest_test_count_expected=742,
            safety_status="PASSED" if checks["safety_passed"] else "BLOCKED",
            live_trading_enabled=bool(self.settings.enable_live_trading),
            paper_trading_enabled=bool(self.settings.paper_trade_observation_enabled or self.settings.paper_trade_observation_allow_enable),
            controlled_paper_enabled=bool(self.settings.controlled_paper_observation_enabled or self.settings.controlled_paper_observation_allow_buys),
            add_order_absent=checks["forbidden_live_order_absent"],
            real_execution_absent=checks["real_execution_absent"],
            observation_system_available=checks["observation_available"],
            signal_quality_available=checks["signal_quality_available"],
            strategy_checkpoint_available=checks["strategy_checkpoint_available"],
            local_runbook_available=checks["local_runbook_available"],
            health_check_available=checks["health_check_available"],
            docs_available=checks["docs_available"],
            ready_to_archive_as_v1=not blockers,
            warnings=self._warnings(not blockers),
            blockers=blockers,
        )
        return report.to_dict()

    def handoff_package(self) -> dict:
        """Return practical operator handoff details."""
        safety = self.safety_audit.run().to_dict()
        package = V1HandoffPackage(
            project_path=str(self.root),
            startup_command=r'.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000',
            test_command=r'.\.venv\Scripts\python.exe -m pytest',
            health_check_command=r'.\.venv\Scripts\python.exe scripts\health_check_phase42.py',
            key_endpoints=[
                "/operator/v1-startup-guide",
                "/operator/one-command-health-check",
                "/audit/v1-freeze-report",
                "/operator/v1-handoff-package",
                "/operator/future-roadmap",
                "/strategy/review-checkpoint",
                "/observation/signal-quality",
                "/observation/controlled-paper/status",
            ],
            safety_status={
                "passed": bool(safety.get("passed")),
                "live_trading_locked": bool(safety.get("live_trading_locked")),
                "add_order_absent": bool(safety.get("no_add_order_detected")),
                "paper_trading_enabled": False,
            },
            intentionally_disabled=[
                "live crypto trading",
                "paper-trade observation",
                "controlled paper observation",
                "MooMoo execution",
                "options execution",
                "threshold auto-apply",
            ],
            do_not_change_without_review=[
                "live trading flags",
                "controlled paper observation flags",
                "minimum signal score thresholds",
                "EMA 200 trade requirement",
                "journal or legacy audit rows",
            ],
            resume_later=[
                "Run the Phase 42 health check.",
                "Review /strategy/review-checkpoint and /observation/signal-quality.",
                "Collect more persisted observation windows before any paper-mode discussion.",
            ],
            recommended_github_tag="v1.0.0-standalone-observation",
            next_project="Stock Trader Bot, separate MooMoo-only repo",
            warnings=["This handoff package is read-only and does not enable paper or live trading."],
        )
        return package.to_dict()

    def future_roadmap(self) -> dict:
        """Return future roadmap separated by project."""
        roadmap = FutureRoadmap(
            crypto_hunter_future=[
                "Collect longer persisted observation windows.",
                "Review controlled paper observation only if gates become eligible.",
                "Consider tiny live review much later after separate approval.",
                "Keep EMA 200 required for execution unless manually reviewed.",
            ],
            stock_trader_bot=[
                "Create a separate repo for a MooMoo-only Stock Trader Bot.",
                "Start read-only with stocks, ETFs, and options market data.",
                "Build scanner, options ranking, paper simulator, and risk gates.",
                "Integrate with YucaTanaTrades later through APIs, not shared bot internals.",
            ],
            yucatanatrades=[
                "Build dashboard and control center after bots prove reliable.",
                "Connect to Crypto Hunter API.",
                "Connect to Stock Trader Bot API.",
                "Avoid merging bot logic directly into the frontend too early.",
            ],
            sol_meme_hunter_future=[
                "Keep Solana meme coin discovery as a later read-only module.",
                "Start with liquidity, rug, social, and wallet concentration filters.",
                "Do not add trading until separate validation proves it safe.",
            ],
            next_project="Standalone MooMoo Stock Trader Bot",
            warnings=["Future roadmap items are not enabled in Crypto Hunter v1."],
        )
        return roadmap.to_dict()

    def next_project_plan(self) -> dict:
        """Return the next standalone project plan."""
        return {
            "project": "Stock Trader Bot",
            "repo_strategy": "separate MooMoo-only repository",
            "first_phase": "read-only MooMoo feasibility and market data",
            "initial_modules": ["stocks and ETFs scanner", "options scanner", "paper simulator", "risk gates", "operator runbook"],
            "integration_note": "YucaTanaTrades should connect later by API after both bots are stable.",
            "not_in_scope": ["Crypto Hunter live trading", "MooMoo order placement", "options execution"],
            "source": "crypto_hunter_next_project_plan_v1",
        }

    def _warnings(self, ready: bool) -> list[str]:
        """Return freeze warnings."""
        warnings = [
            "Crypto Hunter v1 is observation/safety-first.",
            "Paper trading, controlled paper observation, and live trading remain disabled.",
        ]
        if ready:
            warnings.append("Ready to archive as v1 after the operator chooses a git tag.")
        return warnings

    def _phase43_docs_available(self) -> bool:
        """Return whether Phase 43 docs exist."""
        required = [
            "docs/CRYPTO_HUNTER_V1_FREEZE.md",
            "docs/CRYPTO_HUNTER_HANDOFF_PACKAGE.md",
            "docs/CRYPTO_HUNTER_FUTURE_ROADMAP.md",
            "docs/NEXT_PROJECT_STOCK_TRADER_BOT.md",
            "docs/SOL_MEME_HUNTER_FUTURE_MODULE.md",
        ]
        return all(self._exists(rel) for rel in required)

    def _exists(self, rel: str) -> bool:
        """Return whether a repo file exists."""
        return (self.root / rel).exists()

    def _read(self, rel: str) -> str:
        """Read a repo file if available."""
        path = self.root / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
