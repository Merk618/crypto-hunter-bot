"""Observation readiness models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class ObservationReadinessResult:
    """Paper observation readiness result."""

    ready: bool
    checks: dict
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "crypto_hunter_observation_readiness_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)
