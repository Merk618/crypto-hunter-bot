"""Risk readiness wrapper."""

from __future__ import annotations

from app.risk.risk_record_hygiene import RiskRecordHygiene


class RiskReadiness:
    """Read-only risk readiness checks."""

    def __init__(self, hygiene: RiskRecordHygiene | None = None) -> None:
        """Initialize risk readiness."""
        self.hygiene = hygiene or RiskRecordHygiene()

    def check(self, limit: int = 500) -> dict:
        """Return risk readiness report."""
        hygiene = self.hygiene.summary(limit=limit)
        return {
            "ready": bool(hygiene.get("passed")),
            "risk_record_hygiene": hygiene,
            "warnings": [] if hygiene.get("passed") else ["Risk record hygiene requires review before paper-trade observation."],
            "source": "crypto_hunter_risk_readiness_v1",
        }

