"""Serialization helpers for journal records."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

SECRET_KEYS = {"api_key", "api_secret", "secret", "password", "passphrase", "token"}


def to_plain_data(value: Any) -> Any:
    """Convert supported objects to plain JSON-safe data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "to_dict"):
        return scrub_secrets(value.to_dict())
    if is_dataclass(value):
        return scrub_secrets(asdict(value))
    if hasattr(value, "model_dump"):
        return scrub_secrets(value.model_dump())
    if isinstance(value, dict):
        return scrub_secrets({str(k): to_plain_data(v) for k, v in value.items()})
    if isinstance(value, (list, tuple, set)):
        return [to_plain_data(item) for item in value]
    return str(value)


def dumps_json(value: Any) -> str:
    """Dump a supported value as JSON text."""
    return json.dumps(to_plain_data(value), sort_keys=True)


def loads_json(value: str | None) -> Any:
    """Load JSON text, returning None for empty values."""
    if value is None:
        return None
    return json.loads(value)


def scrub_secrets(value: Any) -> Any:
    """Remove secret-looking keys from nested structures."""
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            lower = str(key).lower()
            if any(secret in lower for secret in SECRET_KEYS):
                continue
            output[key] = scrub_secrets(item)
        return output
    if isinstance(value, list):
        return [scrub_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_secrets(item) for item in value)
    return value
