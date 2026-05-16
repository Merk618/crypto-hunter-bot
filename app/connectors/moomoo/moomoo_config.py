"""MooMoo read-only connector configuration helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.config import Settings, get_settings


@dataclass(frozen=True)
class MooMooConnectorConfig:
    """Safe MooMoo connector settings."""

    enabled: bool
    host: str
    port: int
    read_only: bool
    trading_enabled: bool
    paper_trading_enabled: bool
    unlock_trade_context: bool
    account_id_configured: bool
    market_region: str
    source: str = "moomoo_readonly_config_v1"

    def to_dict(self) -> dict:
        """Return a secret-free config dictionary."""
        return asdict(self)


def get_moomoo_config(settings: Settings | None = None) -> MooMooConnectorConfig:
    """Build a safe MooMoo connector config without exposing account identifiers."""
    settings = settings or get_settings()
    return MooMooConnectorConfig(
        enabled=settings.moomoo_enabled,
        host=settings.moomoo_opend_host,
        port=settings.moomoo_opend_port,
        read_only=settings.moomoo_read_only,
        trading_enabled=settings.moomoo_trading_enabled,
        paper_trading_enabled=settings.moomoo_paper_trading_enabled,
        unlock_trade_context=settings.moomoo_unlock_trade_context,
        account_id_configured=bool(settings.moomoo_account_id),
        market_region=settings.moomoo_market_region,
    )
