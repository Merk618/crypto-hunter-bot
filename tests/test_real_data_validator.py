"""Real-data validator tests."""

from app.config import Settings
from app.validation.real_data_validator import RealDataValidator


class Obj:
    """Object with to_dict."""

    def __init__(self, data: dict) -> None:
        self.data = data

    def to_dict(self) -> dict:
        return self.data


class SafeAudit:
    """Passing safety audit."""

    def run(self):
        return Obj({"passed": True, "warnings": [], "blockers": [], "live_trading_locked": True})


class FailingMarketData:
    """Market data service that fails."""

    def get_symbol_ticker(self, symbol: str):
        raise RuntimeError("kraken unavailable")

    def get_symbol_candles(self, symbol: str, timeframe: str, limit: int):
        raise RuntimeError("candles unavailable")


class DisabledMooMoo:
    """Disabled MooMoo health."""

    def get_health(self):
        return Obj({"enabled": False, "connected": False, "read_only": True, "trading_enabled": False, "unlock_trade_context": False})


class DisconnectedMooMoo:
    """Disconnected MooMoo health."""

    def get_health(self):
        return Obj({"enabled": True, "connected": False, "read_only": True, "trading_enabled": False, "unlock_trade_context": False})


class EmptyStockService:
    """Stock service with no external data."""

    def top_candidates(self, limit=3):
        return {"results": []}

    def top_options(self, limit=3):
        return {"top_candidates": []}


class AlertPreview:
    """Alert preview service."""

    def preview_alert_report(self):
        return {"report": {}, "source": "test"}


class Operator:
    """Operator service."""

    def get_operator_status(self):
        return {"live_trading_locked": True, "backend_healthy": True, "warnings": [], "blockers": []}


def validator(**overrides) -> RealDataValidator:
    """Create validator with mocked services."""
    defaults = {
        "settings": Settings(_env_file=None),
        "safety_audit": SafeAudit(),
        "market_data_service": FailingMarketData(),
        "moomoo_client": DisabledMooMoo(),
        "stock_service": EmptyStockService(),
        "alert_service": AlertPreview(),
        "operator_service": Operator(),
    }
    defaults.update(overrides)
    return RealDataValidator(**defaults)


def test_real_data_validator_returns_clean_default_report() -> None:
    """Full report is structured even with unavailable public data."""
    report = validator().run_all_checks()

    assert report["source"] == "crypto_hunter_real_data_validation_v1"
    assert report["checks"]


def test_safety_audit_validation_passes_with_mocked_safe_audit() -> None:
    """Safety audit check passes."""
    check = validator().validate_safety_audit()

    assert check.passed is True


def test_kraken_unavailable_returns_clean_failure_not_crash() -> None:
    """Kraken failure is actionable."""
    check = validator().validate_kraken_public_data()

    assert check.passed is False
    assert check.status == "failed"
    assert check.warnings


def test_moomoo_disabled_returns_clean_warning() -> None:
    """Disabled MooMoo returns warning."""
    check = validator(moomoo_client=DisabledMooMoo()).validate_moomoo_health()

    assert check.status == "disabled"
    assert check.warnings


def test_moomoo_disconnected_returns_clean_warning() -> None:
    """Disconnected MooMoo returns warning."""
    check = validator(moomoo_client=DisconnectedMooMoo()).validate_moomoo_health()

    assert check.status == "disconnected"
    assert check.warnings


def test_crypto_signal_validation_handles_unavailable_data() -> None:
    """Crypto signal failure is clean."""
    check = validator().validate_crypto_signals()

    assert check.passed is False


def test_stock_hunter_validation_handles_disabled_moomoo() -> None:
    """Stock Hunter empty data is warning, not crash."""
    check = validator().validate_stock_hunter()

    assert check.passed is True
    assert check.warnings


def test_options_scanner_validation_handles_unavailable_options() -> None:
    """Options Scanner empty data is warning, not crash."""
    check = validator().validate_options_scanner()

    assert check.passed is True
    assert check.warnings


def test_alerts_reporting_validation_handles_empty_data() -> None:
    """Alerts/reporting preview validates."""
    check = validator().validate_alerts_reporting()

    assert check.passed is True


def test_operator_validation_handles_safe_defaults() -> None:
    """Operator layer validates."""
    check = validator().validate_operator_layer()

    assert check.passed is True
