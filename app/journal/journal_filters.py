"""Production-style journal and candidate filters."""

from __future__ import annotations

import ast
import json
from collections.abc import Iterable

TEST_MARKERS = ("fake", "test", "mock", "demo", "sample", "fixture", "dummy")
NON_PRODUCTION_SOURCES = ("backtest", "dry_run", "demo", "test", "mock")


def normalize_reasons_warnings_blockers(record: dict) -> dict:
    """Normalize reasons/warnings/blockers into clean string lists."""
    cleaned = dict(record)
    for key in ("reasons", "warnings", "blockers"):
        cleaned[key] = _normalize_list(cleaned.get(key) or cleaned.get(f"{key}_json"))
    return cleaned


def is_test_record(record: dict) -> bool:
    """Return True for mock/demo/test/backtest/dry-run records."""
    normalized = normalize_reasons_warnings_blockers(record)
    fields = [
        normalized.get("source"),
        normalized.get("title"),
        normalized.get("category"),
        normalized.get("symbol"),
        normalized.get("reason"),
        normalized.get("message"),
    ]
    fields.extend(normalized.get("reasons", []))
    fields.extend(normalized.get("warnings", []))
    fields.extend(normalized.get("blockers", []))
    text = " ".join(str(value).lower() for value in fields if value is not None)
    source = str(normalized.get("source", "")).lower()
    return any(marker in text for marker in TEST_MARKERS) or any(marker in source for marker in NON_PRODUCTION_SOURCES)


def filter_production_records(records: Iterable[dict]) -> list[dict]:
    """Return records that look production-style."""
    return [normalize_reasons_warnings_blockers(record) for record in records if not is_test_record(record)]


def dedupe_candidates(candidates: Iterable[dict]) -> list[dict]:
    """Dedupe candidates by asset class and symbol, keeping the highest score."""
    best: dict[tuple[str, str], dict] = {}
    for candidate in candidates:
        normalized = normalize_reasons_warnings_blockers(candidate)
        key = (str(normalized.get("asset_class", "")).lower(), str(normalized.get("symbol", "")).upper())
        score = float(normalized.get("score", 0) or 0)
        if key not in best or score > float(best[key].get("score", 0) or 0):
            best[key] = normalized
    return sorted(best.values(), key=lambda item: float(item.get("score", 0) or 0), reverse=True)


def label_record_type(record: dict) -> str:
    """Classify record origin for hygiene summaries."""
    source = str(record.get("source", "")).lower()
    text = json.dumps(record, default=str).lower()
    if "backtest" in source or "backtest" in text:
        return "backtest"
    if "dry_run" in source or "dry-run" in text or "dry run" in text:
        return "dry_run"
    if is_test_record(record):
        if "demo" in text:
            return "demo"
        if "mock" in text:
            return "mock"
        return "test"
    if "paper" in source or "paper" in text:
        return "paper"
    return "real"


def _normalize_list(value) -> list[str]:
    """Convert odd persisted values into clean string lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip() not in {"[", "]", ""}]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in {"", "[]", "[", "]"}:
            return []
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(stripped)
                if isinstance(parsed, list):
                    return _normalize_list(parsed)
            except Exception:
                pass
        return [stripped] if stripped not in {"[", "]"} else []
    return [str(value)]
