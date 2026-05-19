"""Extended observation plan service."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.observation.strategy_review_checkpoint import StrategyReviewCheckpointService
from app.observation.strategy_review_models import ExtendedObservationPlan


class ExtendedObservationPlanService:
    """Create a read-only extended observation plan from the strategy checkpoint."""

    def __init__(self, settings: Settings | None = None, checkpoint_service: StrategyReviewCheckpointService | None = None) -> None:
        """Initialize plan service."""
        self.settings = settings or get_settings()
        self.checkpoint_service = checkpoint_service or StrategyReviewCheckpointService(settings=self.settings)

    def plan(self, checkpoint: dict | None = None) -> dict:
        """Return extended observation plan."""
        checkpoint = checkpoint or self.checkpoint_service.checkpoint()
        focus_symbols = [item.get("symbol") for item in checkpoint.get("strongest_symbols", []) if item.get("symbol")]
        dominant = checkpoint.get("dominant_blockers", [])
        plan = ExtendedObservationPlan(
            plan_status="ACTIVE" if self.settings.extended_observation_plan_enabled else "DISABLED",
            target_additional_runs=self.settings.extended_observation_target_runs,
            target_additional_observations=self.settings.extended_observation_target_observations,
            review_after_runs=self.settings.extended_observation_review_after_runs,
            symbols=list(self.settings.observation_window_symbols),
            timeframe=self.settings.observation_window_timeframe,
            focus_symbols=focus_symbols,
            focus_reasons=self._focus_reasons(checkpoint, dominant),
            observe_only=True,
            paper_trades_allowed=False,
            live_review_allowed=False,
            threshold_changes_allowed=False,
            success_criteria=[
                "Collect repeated STRONG_BUY observations without current risk hygiene issues.",
                "Collect clean risk-approved observations.",
                "Confirm fresh validation and safety audit still pass.",
            ],
            stop_conditions=[
                "Safety audit fails.",
                "Current risk hygiene becomes dirty.",
                "Live trading lock is not confirmed.",
            ],
            review_questions=[
                "Are scores improving by symbol?",
                "Is EMA 200 still the dominant blocker?",
                "Are early recovery candidates becoming stronger or stalling?",
                "Are risk approvals absent because of signal quality or risk rules?",
            ],
            recommended_commands=[
                r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/window/start"',
                r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/window/run-next"',
                r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/strategy/review-checkpoint"',
                r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/signal-quality"',
            ],
        )
        return plan.to_dict()

    def next_step(self) -> dict:
        """Return compact next step."""
        plan = self.plan()
        return {
            "plan_status": plan["plan_status"],
            "next_step": "Run an extended observation window and review the strategy checkpoint.",
            "observe_only": True,
            "paper_trades_allowed": False,
            "live_review_allowed": False,
            "source": "crypto_hunter_extended_observation_next_step_v1",
        }

    def _focus_reasons(self, checkpoint: dict, dominant: list[dict]) -> list[str]:
        """Build focus reasons."""
        reasons = []
        if checkpoint.get("early_recovery_count", 0):
            reasons.append("Early recovery candidates should be monitored as observe-only.")
        if dominant:
            reasons.append("Dominant blockers should be reviewed manually while keeping EMA 200 required.")
        if checkpoint.get("strong_buy_count", 0) == 0:
            reasons.append("No STRONG_BUY observations have appeared yet.")
        if checkpoint.get("risk_approved_count", 0) == 0:
            reasons.append("No risk-approved observations have appeared yet.")
        return reasons or ["Collect a larger persisted observation sample."]
