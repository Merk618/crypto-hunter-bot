"""Risk record hygiene checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.storage.trade_journal import TradeJournal


@dataclass
class RiskRecordInconsistency:
    """One inconsistent risk record."""

    record_id: int | None
    symbol: str
    issue_type: str
    message: str
    severity: str
    metadata: dict = field(default_factory=dict)
    source: str = "crypto_hunter_risk_record_inconsistency_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class RiskRecordHygiene:
    """Preview-only risk decision hygiene scanner."""

    def __init__(self, journal: TradeJournal | None = None) -> None:
        """Initialize hygiene scanner."""
        self.journal = journal or TradeJournal()

    def scan_records(self, records: list[dict] | None = None, limit: int = 500) -> list[RiskRecordInconsistency]:
        """Scan provided or journaled risk records."""
        records = records if records is not None else self.journal.get_recent_risk_decisions(limit=limit)
        inconsistencies: list[RiskRecordInconsistency] = []
        for record in records:
            inconsistencies.extend(self._scan_one(record))
        return inconsistencies

    def summary(self, records: list[dict] | None = None, limit: int = 500) -> dict:
        """Return hygiene summary."""
        inconsistencies = self.scan_records(records=records, limit=limit)
        return {
            "passed": not inconsistencies,
            "inconsistency_count": len(inconsistencies),
            "inconsistencies": [item.to_dict() for item in inconsistencies],
            "preview_only": True,
            "source": "crypto_hunter_risk_record_hygiene_v1",
        }

    def _scan_one(self, record: dict) -> list[RiskRecordInconsistency]:
        """Scan one risk record."""
        output: list[RiskRecordInconsistency] = []
        approved = bool(record.get("approved", False))
        blockers = self._list_field(record.get("blockers"))
        reasons = record.get("reasons")
        warnings = record.get("warnings")
        if not approved:
            for field_name in ("approved_quantity", "max_quantity", "risk_amount"):
                if self._positive(record.get(field_name)):
                    output.append(self._issue(record, f"REJECTED_WITH_{field_name.upper()}", f"approved=false but {field_name} is greater than zero", {"field": field_name, "value": record.get(field_name)}))
        if approved and blockers:
            output.append(self._issue(record, "APPROVED_WITH_BLOCKERS", "approved=true but blockers are present", {"blockers": blockers}))
        if not str(record.get("symbol", "")).strip():
            output.append(self._issue(record, "MISSING_SYMBOL", "risk record is missing symbol", severity="HIGH"))
        if str(record.get("side", "")).strip().lower() not in {"buy", "sell"}:
            output.append(self._issue(record, "MISSING_OR_INVALID_SIDE", "risk record side is missing or invalid", severity="HIGH"))
        for field_name, value in (("blockers", blockers), ("reasons", reasons), ("warnings", warnings)):
            if value is not None and not isinstance(value, list):
                output.append(self._issue(record, f"MALFORMED_{field_name.upper()}", f"{field_name} should be a list", {"value": value}, severity="LOW"))
        return output

    def _issue(self, record: dict, issue_type: str, message: str, metadata: dict | None = None, severity: str = "MEDIUM") -> RiskRecordInconsistency:
        """Build an issue."""
        return RiskRecordInconsistency(
            record_id=record.get("id"),
            symbol=str(record.get("symbol", "")),
            issue_type=issue_type,
            message=message,
            severity=severity,
            metadata=metadata or {},
        )

    def _positive(self, value: Any) -> bool:
        """Return True when value is numeric and positive."""
        try:
            return value is not None and float(value) > 0
        except (TypeError, ValueError):
            return False

    def _list_field(self, value: Any) -> list:
        """Return list field safely."""
        return value if isinstance(value, list) else []

