"""Risk record hygiene checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import Settings, get_settings
from app.storage.serializers import normalize_rejected_risk_payload
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

    def __init__(self, journal: TradeJournal | None = None, settings: Settings | None = None) -> None:
        """Initialize hygiene scanner."""
        self.journal = journal or TradeJournal()
        self.settings = settings or get_settings()

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
            "classification": self.summarize_by_classification(records=records, limit=limit),
            "preview_only": True,
            "source": "crypto_hunter_risk_record_hygiene_v1",
        }

    def classify_risk_record(self, record: dict) -> dict:
        """Classify one risk record without mutating it."""
        issues = self._scan_one(record)
        approved = bool(record.get("approved", False))
        if not str(record.get("symbol", "")).strip() or str(record.get("side", "")).strip().lower() not in {"buy", "sell"}:
            classification = "MALFORMED_RECORD"
        elif issues and not approved and self.is_legacy_inconsistency(record):
            classification = "LEGACY_INCONSISTENT_REJECTED_RECORD"
        elif issues and not approved:
            classification = "CURRENT_INCONSISTENT_REJECTED_RECORD"
        elif approved and not issues:
            classification = "CLEAN_APPROVED_RECORD"
        elif not approved and not issues:
            classification = "CLEAN_REJECTED_RECORD"
        else:
            classification = "MALFORMED_RECORD"
        return {
            "record_id": record.get("id"),
            "symbol": record.get("symbol"),
            "classification": classification,
            "issues": [issue.to_dict() for issue in issues],
            "recommended_action": self._recommendation(classification),
            "preview_only": True,
        }

    def summarize_by_classification(self, records: list[dict] | None = None, limit: int | None = None) -> dict:
        """Summarize risk records by classification."""
        if records is None:
            records = self.journal.get_recent_risk_decisions(limit=limit or self.settings.risk_hygiene_recent_record_limit)
        counts: dict[str, int] = {}
        for record in records:
            classification = self.classify_risk_record(record)["classification"]
            counts[classification] = counts.get(classification, 0) + 1
        return counts

    def preview_remediation_plan(self, records: list[dict] | None = None, limit: int | None = None) -> dict:
        """Return a read-only remediation preview."""
        if records is None:
            records = self.journal.get_recent_risk_decisions(limit=limit or self.settings.risk_hygiene_recent_record_limit)
        classified = [self.classify_risk_record(record) for record in records]
        return {
            "preview_only": True,
            "destructive_cleanup_allowed": False,
            "classifications": classified,
            "summary": self.summarize_by_classification(records),
            "recommended_actions": [
                "Keep legacy records for audit history.",
                "Use Phase 31 normalized persistence for future rejected risk decisions.",
                "Do not delete or mutate journal rows automatically.",
            ],
            "source": "crypto_hunter_risk_hygiene_remediation_preview_v1",
        }

    def validate_recent_records_only(self, limit: int | None = None) -> dict:
        """Validate only recent records according to configured limit."""
        limit = limit or self.settings.risk_hygiene_current_record_lookback
        records = self.journal.get_recent_risk_decisions(limit=limit)
        return self.validate_recent_records_only_from_records(records, limit)

    def validate_recent_records_only_from_records(self, records: list[dict], limit: int | None = None) -> dict:
        """Validate provided recent records."""
        limit = limit or len(records)
        inconsistencies = self.scan_records(records=records)
        current = [issue for issue in inconsistencies if not self.is_legacy_inconsistency(self._record_by_id(records, issue.record_id))]
        legacy = [issue for issue in inconsistencies if self.is_legacy_inconsistency(self._record_by_id(records, issue.record_id))]
        legacy_warn_only = self.settings.risk_hygiene_legacy_records_warn_only and not self.settings.risk_hygiene_legacy_records_block_paper_readiness
        blocking = current + ([] if legacy_warn_only else legacy)
        warnings = []
        if legacy:
            warnings.append("Legacy risk records remain in audit history and are not deleted.")
        return {
            "passed": not blocking,
            "recent_limit": limit,
            "current_clean": not current,
            "legacy_present": bool(legacy),
            "legacy_warn_only": legacy_warn_only,
            "current_inconsistency_count": len(current),
            "legacy_inconsistency_count": len(legacy),
            "blocking_inconsistency_count": len(blocking),
            "warnings": warnings,
            "blockers": [issue.message for issue in current],
            "preview_only": True,
            "source": "crypto_hunter_risk_recent_cleanliness_v1",
        }

    def legacy_aware_readiness(self, records: list[dict] | None = None, limit: int | None = None) -> dict:
        """Return legacy-aware risk readiness."""
        if records is None:
            records = self.journal.get_recent_risk_decisions(limit=limit or self.settings.risk_hygiene_current_record_lookback)
        classification_summary = self.summarize_by_classification(records)
        recent = self.validate_recent_records_only_from_records(records, limit or len(records))
        warnings = list(recent.get("warnings", []))
        blockers = list(recent.get("blockers", []))
        return {
            "passed": bool(recent.get("passed")),
            "current_clean": bool(recent.get("current_clean")),
            "legacy_present": bool(recent.get("legacy_present")),
            "legacy_warn_only": bool(recent.get("legacy_warn_only")),
            "current_inconsistency_count": recent.get("current_inconsistency_count", 0),
            "legacy_inconsistency_count": recent.get("legacy_inconsistency_count", 0),
            "blocking_inconsistency_count": recent.get("blocking_inconsistency_count", 0),
            "classification_summary": classification_summary,
            "warnings": warnings,
            "blockers": blockers,
            "source": "crypto_hunter_legacy_aware_risk_readiness_v1",
        }

    def normalize_rejected_decision_payload(self, payload: dict) -> dict:
        """Normalize rejected risk decision payload for future persistence."""
        return normalize_rejected_risk_payload(payload)

    def is_legacy_inconsistency(self, record: dict | None) -> bool:
        """Return whether inconsistent row appears to predate Phase 31 normalization."""
        if not record:
            return False
        if bool(record.get("approved", False)):
            return False
        source = str(record.get("source", ""))
        return source == "crypto_hunter_risk_v1" and any(self._positive(record.get(field)) for field in ("approved_quantity", "max_quantity", "risk_amount"))

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

    def _recommendation(self, classification: str) -> str:
        """Return read-only recommendation for classification."""
        if classification == "LEGACY_INCONSISTENT_REJECTED_RECORD":
            return "Keep for audit; future Phase 31 records are normalized before persistence."
        if classification == "CURRENT_INCONSISTENT_REJECTED_RECORD":
            return "Investigate current risk persistence path before paper-trade observation."
        if classification == "MALFORMED_RECORD":
            return "Review malformed risk journal payload."
        return "No remediation needed."

    def _record_by_id(self, records: list[dict], record_id: int | None) -> dict | None:
        """Find a record by id."""
        for record in records:
            if record.get("id") == record_id:
                return record
        return None
