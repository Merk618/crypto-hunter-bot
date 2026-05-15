"""Account service tests."""

import base64
from datetime import datetime, timedelta, timezone

from app.account.account_service import AccountService
from app.config import Settings
from app.exchanges.kraken_account_models import ExchangeAccountSummary, ExchangeBalance


class FakeClient:
    """Fake private client."""

    def __init__(self, configured: bool = True) -> None:
        """Initialize fake client."""
        self.configured = configured
        self.calls = 0

    def is_configured(self) -> bool:
        """Return configured flag."""
        return self.configured

    def get_account_summary(self) -> ExchangeAccountSummary:
        """Return fake account summary."""
        self.calls += 1
        return ExchangeAccountSummary(
            exchange="kraken",
            private_read_enabled=True,
            configured=True,
            balances=[ExchangeBalance("XXBT", 1.0)],
            total_assets_count=1,
            nonzero_assets_count=1,
            warnings=[],
        )


def fake_secret() -> str:
    """Return fake base64 secret."""
    return base64.b64encode(b"secret").decode("utf-8")


def settings(**overrides) -> Settings:
    """Build service settings."""
    base = {"KRAKEN_PRIVATE_READ_ENABLED": True, "KRAKEN_API_KEY": "key", "KRAKEN_API_SECRET": fake_secret(), "KRAKEN_ACCOUNT_CACHE_SECONDS": 30}
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_account_service_returns_disabled_state_safely() -> None:
    """Disabled private read returns safe summary."""
    service = AccountService(client=FakeClient(), settings=settings(KRAKEN_PRIVATE_READ_ENABLED=False))  # type: ignore[arg-type]
    summary = service.get_account_summary()
    assert summary.private_read_enabled is False
    assert summary.balances == []
    assert "disabled" in summary.warnings[0]


def test_account_service_returns_missing_key_state_safely() -> None:
    """Missing keys return configured false."""
    service = AccountService(client=FakeClient(configured=False), settings=settings())  # type: ignore[arg-type]
    summary = service.get_account_summary()
    assert summary.configured is False
    assert "missing" in summary.warnings[0]


def test_account_service_returns_account_summary_from_mocked_kraken_response() -> None:
    """Configured service returns client summary."""
    client = FakeClient()
    service = AccountService(client=client, settings=settings())  # type: ignore[arg-type]
    summary = service.get_account_summary()
    assert summary.total_assets_count == 1
    assert summary.balances[0].asset == "XXBT"


def test_account_service_caches_result_within_cache_window() -> None:
    """Service caches account summary."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    client = FakeClient()
    service = AccountService(client=client, settings=settings(), now_fn=lambda: now)  # type: ignore[arg-type]
    service.get_account_summary()
    service.get_account_summary()
    assert client.calls == 1


def test_account_service_does_not_expose_api_key_or_secret() -> None:
    """Status and summaries do not include credentials."""
    service = AccountService(client=FakeClient(), settings=settings())  # type: ignore[arg-type]
    text = str(service.get_status()) + str(service.get_account_summary().to_dict())
    assert "api_key" not in text.lower()
    assert "secret" not in text.lower()
    assert "key" not in text
