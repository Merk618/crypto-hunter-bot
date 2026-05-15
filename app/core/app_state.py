"""Application runtime state summary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.config import Settings, get_settings
from app.core.dependencies import dependency_status, get_execution_guard
from app.storage.serializers import scrub_secrets


@dataclass
class AppState:
    """Read-only runtime state for system endpoints."""

    settings: Settings = field(default_factory=get_settings)
    app_started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_health_check_at: datetime | None = None

    def get_runtime_summary(self) -> dict[str, Any]:
        """Return a safe runtime summary without secrets."""
        self.last_health_check_at = datetime.now(timezone.utc)
        summary = {
            "app_started_at": self.app_started_at.isoformat(),
            "environment_mode": "local",
            "bot_mode": self.settings.bot_mode.value,
            "live_trading_enabled": self.settings.enable_live_trading,
            "dry_run_enabled": self.settings.dry_run_execution_enabled,
            "journal_enabled": self.settings.enable_trade_journal,
            "private_read_enabled": self.settings.kraken_private_read_enabled,
            "safety_status": get_execution_guard().get_execution_safety_status(),
            "dependency_status": dependency_status(),
            "last_health_check_at": self.last_health_check_at.isoformat(),
        }
        return scrub_secrets(summary)

    def to_dict(self) -> dict[str, Any]:
        """Return dataclass contents with datetime values serialized."""
        data = asdict(self)
        data.pop("settings", None)
        for key, value in list(data.items()):
            if hasattr(value, "isoformat"):
                data[key] = value.isoformat()
        return scrub_secrets(data)
