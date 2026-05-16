"""MooMoo health tests."""

from app.config import Settings
from app.connectors.moomoo.moomoo_health import MooMooHealth


def test_health_checker_handles_missing_moomoo_api() -> None:
    """Missing moomoo-api produces a clean unavailable status."""
    health = MooMooHealth(Settings(_env_file=None), import_checker=lambda _: False).check()

    assert health.import_available is False
    assert health.connected is False
    assert any("not importable" in warning for warning in health.warnings)


def test_health_checker_handles_available_moomoo_api_mock() -> None:
    """Import-available mock reports cleanly while disabled."""
    health = MooMooHealth(Settings(_env_file=None), import_checker=lambda _: True).check()

    assert health.import_available is True
    assert health.enabled is False
    assert health.connected is False


def test_health_checker_handles_opend_disconnected_cleanly() -> None:
    """Enabled MooMoo with closed OpenD reports disconnected without raising."""
    settings = Settings(_env_file=None, MOOMOO_ENABLED=True)
    health = MooMooHealth(settings, import_checker=lambda _: True, socket_checker=lambda host, port: False).check()

    assert health.enabled is True
    assert health.import_available is True
    assert health.connected is False
    assert any("OpenD socket is not reachable" in warning for warning in health.warnings)
