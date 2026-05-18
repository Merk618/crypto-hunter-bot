"""Controlled paper-only observation infrastructure."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.execution.trade_executor import TradeExecutor
from app.observation.controlled_paper_models import (
    ControlledPaperObservationDecision,
    ControlledPaperObservationRequest,
    ControlledPaperObservationRun,
    ControlledPaperObservationStatus,
    ControlledPaperTradePreview,
    now_utc,
)
from app.observation.fresh_observation_validator import FreshObservationValidator
from app.observation.observation_hydration import ObservationHydrationService
from app.observation.observation_metrics import flatten_results
from app.observation.paper_trade_approval_gate import PaperTradeApprovalGate
from app.observation.paper_trade_readiness import PaperTradeReadinessService
from app.risk.risk_record_hygiene import RiskRecordHygiene


class ControlledPaperObservationService:
    """Approval-gated controlled paper observation service."""

    def __init__(
        self,
        settings: Settings | None = None,
        hydration: ObservationHydrationService | None = None,
        approval_gate: PaperTradeApprovalGate | None = None,
        fresh_validator: FreshObservationValidator | None = None,
        risk_hygiene: RiskRecordHygiene | None = None,
        readiness: PaperTradeReadinessService | None = None,
        trade_executor: TradeExecutor | None = None,
    ) -> None:
        """Initialize service."""
        self.settings = settings or get_settings()
        self.hydration = hydration or ObservationHydrationService(settings=self.settings)
        self.risk_hygiene = risk_hygiene or RiskRecordHygiene(settings=self.settings)
        self.fresh_validator = fresh_validator or FreshObservationValidator(settings=self.settings, hydration=self.hydration, hygiene=self.risk_hygiene)
        self.approval_gate = approval_gate or PaperTradeApprovalGate(settings=self.settings, hydration=self.hydration, risk_hygiene=self.risk_hygiene)
        self.readiness = readiness or PaperTradeReadinessService(settings=self.settings, hydration=self.hydration, risk_hygiene=self.risk_hygiene)
        self.trade_executor = trade_executor or TradeExecutor(settings=self.settings)
        self.recent_runs: list[dict] = []
        self._trades_today = 0

    def status(self) -> dict:
        """Return controlled paper status."""
        return ControlledPaperObservationStatus(
            enabled=self.settings.controlled_paper_observation_enabled,
            approval_required=self.settings.controlled_paper_observation_require_approval,
            operator_start_required=self.settings.controlled_paper_observation_require_operator_start,
            buys_allowed=self.settings.controlled_paper_observation_allow_buys,
            sells_allowed=self.settings.controlled_paper_observation_allow_sells,
            max_notional_per_trade=self.settings.controlled_paper_observation_max_notional_per_trade,
            max_trades_per_run=self.settings.controlled_paper_observation_max_trades_per_run,
            max_trades_per_day=self.settings.controlled_paper_observation_max_trades_per_day,
            allowed_symbols=self.settings.controlled_paper_observation_allowed_symbols,
            paper_trade_observation_enabled=self.settings.paper_trade_observation_enabled,
            live_trading_locked=not self.settings.enable_live_trading,
        ).to_dict()

    def evaluate(self, request: ControlledPaperObservationRequest | None = None, runs: list[dict] | None = None) -> dict:
        """Evaluate whether controlled paper observation may proceed."""
        request = request or ControlledPaperObservationRequest()
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        approval = self.approval_gate.evaluate(runs=runs)
        fresh = self.fresh_validator.validate(runs=runs)
        readiness = self.readiness.check(runs=[run for run in runs if run.get("status") == "completed"])
        risk = self.risk_hygiene.legacy_aware_readiness()
        blockers: list[str] = []
        warnings: list[str] = []
        status = "PREVIEW_ONLY"
        if self.settings.controlled_paper_observation_require_operator_start and not request.manual_start:
            blockers.append("manual_start=true is required")
            status = "REFUSED"
        if self.settings.controlled_paper_observation_require_operator_start and not request.operator_acknowledged:
            blockers.append("operator_acknowledged=true is required")
            status = "REFUSED"
        if not self.settings.controlled_paper_observation_enabled or not self.settings.paper_trade_observation_enabled:
            blockers.append("controlled paper observation disabled by config")
            status = "DISABLED_BY_CONFIG"
        if self.settings.controlled_paper_observation_require_approval_gate and approval.get("approval_status") != "ELIGIBLE_FOR_OPERATOR_REVIEW":
            blockers.append("approval gate is not eligible for operator review")
            status = "BLOCKED_BY_APPROVAL_GATE"
        if self.settings.controlled_paper_observation_require_fresh_validation and not fresh.get("passed"):
            blockers.append("fresh validation has not passed")
            status = "BLOCKED_BY_FRESH_VALIDATION"
        if self.settings.risk_hygiene_require_current_cleanliness and not risk.get("current_clean", False):
            blockers.append("current risk hygiene is not clean")
            status = "BLOCKED_BY_RISK_HYGIENE"
        results = flatten_results([run for run in runs if run.get("status") == "completed"])
        strong = [result for result in results if self._signal_ok(result)]
        approved = [result for result in strong if (result.get("risk_decision") or {}).get("approved")]
        if not strong and self.settings.controlled_paper_observation_require_strong_buy:
            blockers.append("no STRONG_BUY signals available")
            status = "NOT_READY"
        if not approved and self.settings.controlled_paper_observation_require_risk_approved:
            blockers.append("no risk-approved signals available")
            status = "NOT_READY"
        allowed = not blockers
        if allowed and not self.settings.controlled_paper_observation_allow_buys:
            warnings.append("buys disabled; preview only")
            status = "PREVIEW_ONLY"
        return ControlledPaperObservationDecision(
            allowed=allowed,
            status=status if blockers or warnings else "PAPER_OBSERVATION_RUN_COMPLETED",
            message="Controlled paper observation evaluation complete",
            blockers=list(dict.fromkeys(blockers)),
            warnings=list(dict.fromkeys(warnings)),
            approval_gate_status=approval.get("approval_status"),
            fresh_validation_status=fresh.get("status"),
            paper_trade_readiness_status=readiness.get("decision"),
            risk_hygiene_status="CURRENT_CLEAN" if risk.get("current_clean") else "CURRENT_BLOCKED",
        ).to_dict()

    def preview(self, request: ControlledPaperObservationRequest | None = None, runs: list[dict] | None = None) -> dict:
        """Create controlled paper trade previews without trading."""
        request = request or ControlledPaperObservationRequest()
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        decision = self.evaluate(request, runs)
        previews = self._build_previews(runs, allow_execution=False)
        return {"decision": decision, "previews": previews, "paper_trades_created": 0, "source": "crypto_hunter_controlled_paper_preview_v1"}

    def run_once(self, request: ControlledPaperObservationRequest | None = None, runs: list[dict] | None = None) -> dict:
        """Run one controlled paper observation pass."""
        request = request or ControlledPaperObservationRequest()
        runs = runs if runs is not None else self.hydration.load_recent_runs(limit=self.settings.observation_history_limit)
        started = now_utc()
        decision = self.evaluate(request, runs)
        previews = self._build_previews(runs, allow_execution=decision.get("allowed", False))
        trade_results: list[dict] = []
        if self._may_execute(request, decision):
            for preview in previews[: self._trade_limit(request)]:
                if self._trades_today >= self.settings.controlled_paper_observation_max_trades_per_day:
                    break
                trade_results.append(self._execute_preview(preview, request.reason))
                self._trades_today += 1
        run = ControlledPaperObservationRun(
            run_id=str(uuid.uuid4()),
            status=decision.get("status", "REFUSED") if not trade_results else "PAPER_OBSERVATION_RUN_COMPLETED",
            started_at=started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            symbols_processed=len({preview["symbol"] for preview in previews}),
            signals_generated=len(previews),
            risk_decisions_generated=len(previews),
            paper_trade_previews_created=len(previews),
            paper_trades_created=len(trade_results),
            blocked_trades=max(0, len(previews) - len(trade_results)),
            warnings=list(decision.get("warnings", [])),
            blockers=list(decision.get("blockers", [])),
            previews=previews,
            trade_results=trade_results,
        ).to_dict()
        self.recent_runs.insert(0, run)
        self.recent_runs = self.recent_runs[:50]
        return run

    def recent(self, limit: int = 50) -> dict:
        """Return recent controlled paper runs."""
        return {"runs": self.recent_runs[:limit], "source": "crypto_hunter_controlled_paper_recent_v1"}

    def _build_previews(self, runs: list[dict], allow_execution: bool) -> list[dict]:
        """Build trade previews from eligible observed signals."""
        results = flatten_results([run for run in runs if run.get("status") == "completed"])
        previews: list[dict] = []
        for result in results:
            symbol = str(result.get("symbol") or "").upper().replace("-", "/")
            if symbol not in self.settings.controlled_paper_observation_allowed_symbols:
                continue
            if not self._signal_ok(result) or not (result.get("risk_decision") or {}).get("approved"):
                continue
            signal = result.get("signal") or {}
            price = float(signal.get("latest_price") or signal.get("suggested_entry") or 100.0)
            requested = float((result.get("risk_decision") or {}).get("estimated_notional") or self.settings.controlled_paper_observation_max_notional_per_trade)
            capped = min(requested, self.settings.controlled_paper_observation_max_notional_per_trade)
            qty = capped / price if price > 0 else 0.0
            preview = ControlledPaperTradePreview(
                symbol=symbol,
                side="buy",
                signal_score=float(signal.get("score", 0) or 0),
                signal_category=str(signal.get("category", "")),
                risk_approved=True,
                estimated_price=price,
                requested_notional=requested,
                capped_notional=capped,
                estimated_quantity=qty,
                fees_estimate=capped * self.settings.paper_fee_rate,
                slippage_estimate=capped * (self.settings.paper_slippage_bps / 10000),
                allowed_for_execution=allow_execution and self.settings.controlled_paper_observation_allow_buys,
                warnings=["CONTROLLED_PAPER_OBSERVATION preview; broker=PAPER; real_execution=false; live_trade=false"],
            ).to_dict()
            previews.append(preview)
        return previews

    def _signal_ok(self, result: dict) -> bool:
        """Return whether result has qualifying signal."""
        signal = result.get("signal") or {}
        if float(signal.get("score", 0) or 0) < self.settings.controlled_paper_observation_min_signal_score:
            return False
        if self.settings.controlled_paper_observation_require_strong_buy and signal.get("category") != "STRONG_BUY":
            return False
        return True

    def _may_execute(self, request: ControlledPaperObservationRequest, decision: dict) -> bool:
        """Return whether request may execute paper trades."""
        return bool(
            decision.get("allowed")
            and request.allow_paper_trade_execution
            and self.settings.controlled_paper_observation_enabled
            and self.settings.paper_trade_observation_enabled
            and self.settings.controlled_paper_observation_allow_buys
        )

    def _trade_limit(self, request: ControlledPaperObservationRequest) -> int:
        """Return max trades for this run."""
        requested = request.max_trades if request.max_trades is not None else self.settings.controlled_paper_observation_max_trades_per_run
        return max(0, min(int(requested), self.settings.controlled_paper_observation_max_trades_per_run))

    def _execute_preview(self, preview: dict, reason: str) -> dict:
        """Execute one preview through PaperBroker only."""
        result = self.trade_executor.execute_paper_market_order(preview["symbol"], "buy", preview["estimated_quantity"], preview["estimated_price"], f"CONTROLLED_PAPER_OBSERVATION: {reason}")
        result["mode"] = "CONTROLLED_PAPER_OBSERVATION"
        result["real_execution"] = False
        result["live_trade"] = False
        result["broker"] = "PAPER"
        return result
