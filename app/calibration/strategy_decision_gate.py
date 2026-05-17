"""Read-only strategy decision gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.config import Settings, get_settings
from app.observation.early_recovery import EarlyRecoveryClassifier
from app.observation.observation_metrics import flatten_results, summarize_blockers


@dataclass
class StrategyDecisionReport:
    """Strategy decision gate report."""

    decision: str
    confidence: str
    observations_analyzed: int
    completed_runs_analyzed: int
    dominant_blockers: list[dict] = field(default_factory=list)
    strongest_symbols: list[dict] = field(default_factory=list)
    early_recovery_candidates: list[dict] = field(default_factory=list)
    paper_trade_observation_allowed: bool = False
    live_review_allowed: bool = False
    findings: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_strategy_decision_gate_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class StrategyDecisionGate:
    """Make read-only next-step decisions from observation and calibration data."""

    def __init__(self, settings: Settings | None = None, safety_audit=None, early_recovery: EarlyRecoveryClassifier | None = None) -> None:
        """Initialize decision gate."""
        self.settings = settings or get_settings()
        self.safety_audit = safety_audit
        self.early_recovery = early_recovery or EarlyRecoveryClassifier(self.settings)

    def evaluate(self, runs: list[dict], safety_report: dict | None = None) -> StrategyDecisionReport:
        """Evaluate strategy next-step decision without mutating config."""
        completed_runs = [run for run in runs if run.get("status") == "completed"]
        results = flatten_results(completed_runs)
        safety = safety_report if safety_report is not None else self._run_safety()
        if safety and not safety.get("passed", False):
            return StrategyDecisionReport(
                decision="BLOCKED",
                confidence="HIGH",
                observations_analyzed=len(results),
                completed_runs_analyzed=len(completed_runs),
                blockers=list(safety.get("blockers") or ["safety audit failed"]),
                findings=["Safety audit did not pass."],
                recommended_next_actions=["Resolve safety audit blockers before continuing observation decisions."],
            )
        dominant = self._dominant_blockers(results)
        strongest = self._strongest_symbols(results)
        candidates = [candidate.to_dict() for candidate in self.early_recovery.classify_results(results)]
        if len(results) < 20:
            return StrategyDecisionReport(
                decision="KEEP_OBSERVING",
                confidence="LOW",
                observations_analyzed=len(results),
                completed_runs_analyzed=len(completed_runs),
                dominant_blockers=dominant,
                strongest_symbols=strongest,
                early_recovery_candidates=candidates,
                findings=["Observation sample is below 20 results."],
                recommended_next_actions=["Continue paper observation windows before strategy changes."],
                warnings=["No thresholds or trade permissions are changed."],
            )
        if self._ema_200_dominant(dominant) and candidates:
            return StrategyDecisionReport(
                decision="ADD_EARLY_RECOVERY_WATCHLIST",
                confidence="MEDIUM",
                observations_analyzed=len(results),
                completed_runs_analyzed=len(completed_runs),
                dominant_blockers=dominant,
                strongest_symbols=strongest,
                early_recovery_candidates=candidates,
                paper_trade_observation_allowed=False,
                live_review_allowed=False,
                findings=["EMA 200 is dominant while repeated neutral candidates show momentum evidence."],
                recommended_next_actions=[
                    "Add an observation-only early recovery watchlist tag in a future phase.",
                    "Keep EMA 200 required for trade execution.",
                    "Continue collecting observation windows before paper-trade observation.",
                ],
            )
        if self._has_repeated_strong_buy_with_risk(results) and self.settings.allow_paper_trade_observation:
            return StrategyDecisionReport(
                decision="ALLOW_PAPER_TRADE_OBSERVATION",
                confidence="MEDIUM",
                observations_analyzed=len(results),
                completed_runs_analyzed=len(completed_runs),
                dominant_blockers=dominant,
                strongest_symbols=strongest,
                early_recovery_candidates=candidates,
                paper_trade_observation_allowed=True,
                live_review_allowed=False,
                findings=["Repeated STRONG_BUY signals with paper risk approvals were observed."],
                recommended_next_actions=["Paper-trade observation may be reviewed manually; live review remains blocked."],
            )
        return StrategyDecisionReport(
            decision="KEEP_OBSERVING",
            confidence="MEDIUM",
            observations_analyzed=len(results),
            completed_runs_analyzed=len(completed_runs),
            dominant_blockers=dominant,
            strongest_symbols=strongest,
            early_recovery_candidates=candidates,
            findings=["No higher-confidence decision gate condition has been met."],
            recommended_next_actions=["Continue observation-only mode."],
            warnings=["Live review remains disabled in this phase."],
        )

    def _run_safety(self) -> dict:
        """Run safety audit if provided, otherwise assume safe for pure unit use."""
        if self.safety_audit is None:
            return {"passed": True, "blockers": []}
        result = self.safety_audit.run()
        return result.to_dict() if hasattr(result, "to_dict") else dict(result)

    def _dominant_blockers(self, results: list[dict]) -> list[dict]:
        """Return blocker ranking."""
        return [{"text": text, "count": count} for text, count in sorted(summarize_blockers(results).items(), key=lambda item: item[1], reverse=True)[:5]]

    def _strongest_symbols(self, results: list[dict]) -> list[dict]:
        """Return strongest observed symbols by max/latest score."""
        strongest: dict[str, dict[str, Any]] = {}
        for result in results:
            signal = result.get("signal") or {}
            symbol = str(result.get("symbol") or signal.get("symbol") or "UNKNOWN").upper().replace("-", "/")
            score = float(signal.get("score", 0) or 0)
            current = strongest.setdefault(symbol, {"symbol": symbol, "max_score": score, "latest_score": score, "category": signal.get("category")})
            current["max_score"] = max(current["max_score"], score)
            current["latest_score"] = score
            current["category"] = signal.get("category")
        return sorted(strongest.values(), key=lambda item: (item["max_score"], item["latest_score"]), reverse=True)

    def _ema_200_dominant(self, dominant: list[dict]) -> bool:
        """Return whether EMA 200 is a dominant blocker."""
        return any(("ema 200" in item["text"].lower() or "ema_200" in item["text"].lower() or "ema200" in item["text"].lower()) for item in dominant)

    def _has_repeated_strong_buy_with_risk(self, results: list[dict]) -> bool:
        """Return whether repeated strong buy risk-approved observations exist."""
        count = 0
        for result in results:
            signal = result.get("signal") or {}
            risk = result.get("risk_decision") or {}
            if signal.get("category") == "STRONG_BUY" and risk.get("approved"):
                count += 1
        return count >= 2

