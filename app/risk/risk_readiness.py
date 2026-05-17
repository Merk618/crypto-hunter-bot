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
        recent = self.hygiene.validate_recent_records_only(limit=limit)
        legacy_aware = self.hygiene.legacy_aware_readiness(limit=limit)
        warnings = list(legacy_aware.get("warnings", []))
        if not recent.get("passed"):
            warnings.append("Risk record hygiene requires review before paper-trade observation.")
        return {
            "ready": bool(recent.get("passed")),
            "risk_record_hygiene": hygiene,
            "recent_cleanliness": recent,
            "legacy_aware_readiness": legacy_aware,
            "warnings": list(dict.fromkeys(warnings)),
            "source": "crypto_hunter_risk_readiness_v1",
        }
