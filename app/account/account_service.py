"""Read-only exchange account service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import Settings, get_settings
from app.exchanges.kraken_account_models import ExchangeAccountSummary
from app.exchanges.kraken_private_client import KrakenPrivateClient
from app.storage.trade_journal import TradeJournal


class AccountService:
    """Safe read-only account service with cache and journaled errors."""

    def __init__(self, client: KrakenPrivateClient | None = None, settings: Settings | None = None, journal: TradeJournal | None = None, now_fn=None) -> None:
        """Initialize account service."""
        self.settings = settings or get_settings()
        self.client = client or KrakenPrivateClient(settings=self.settings)
        self.journal = journal
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._cached_summary: ExchangeAccountSummary | None = None
        self._cached_at: datetime | None = None

    def get_status(self) -> dict:
        """Return safe account connectivity status."""
        return {
            "exchange": "kraken",
            "private_read_enabled": self.settings.kraken_private_read_enabled,
            "private_trading_enabled": self.settings.kraken_private_trading_enabled,
            "require_read_only": self.settings.kraken_require_read_only,
            "configured": self.client.is_configured(),
            "source": "kraken_private_read_v1",
        }

    def get_account_summary(self) -> ExchangeAccountSummary:
        """Return safe read-only account summary."""
        if not self.settings.kraken_private_read_enabled:
            return self._disabled_summary("Kraken private account read is disabled")
        if not self.client.is_configured():
            return self._disabled_summary("Kraken private API credentials are missing")
        if self._cache_valid():
            assert self._cached_summary is not None
            return self._cached_summary
        try:
            summary = self.client.get_account_summary()
            if self.settings.kraken_private_trading_enabled:
                summary.warnings.append("KRAKEN_PRIVATE_TRADING_ENABLED=true but this phase remains read-only")
            self._cached_summary = summary
            self._cached_at = self._now_fn()
            return summary
        except Exception as exc:  # noqa: BLE001
            self._record_error(type(exc).__name__, str(exc))
            return self._disabled_summary(f"Kraken private account read failed: {type(exc).__name__}")

    def get_balances(self) -> list[dict]:
        """Return safe account balances."""
        return [balance.to_dict() for balance in self.get_account_summary().balances]

    def _cache_valid(self) -> bool:
        """Return whether cached summary is still valid."""
        if self._cached_summary is None or self._cached_at is None:
            return False
        return self._now_fn() - self._cached_at <= timedelta(seconds=self.settings.kraken_account_cache_seconds)

    def _disabled_summary(self, warning: str) -> ExchangeAccountSummary:
        """Return safe disabled summary."""
        return ExchangeAccountSummary(
            exchange="kraken",
            private_read_enabled=self.settings.kraken_private_read_enabled,
            configured=self.client.is_configured(),
            balances=[],
            total_assets_count=0,
            nonzero_assets_count=0,
            warnings=[warning],
        )

    def _record_error(self, error_type: str, message: str) -> None:
        """Record account read error without raising."""
        if not self.journal:
            return
        try:
            self.journal.record_error("account_service", error_type, message)
        except Exception:
            return
