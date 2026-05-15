"""App state tests."""

from app.core.app_state import AppState


def test_app_state_runtime_summary_does_not_expose_secrets() -> None:
    """Runtime summary should be safe for API responses."""
    summary = AppState().get_runtime_summary()
    text = str(summary).lower()

    assert summary["bot_mode"] == "paper"
    assert summary["live_trading_enabled"] is False
    assert "api_key" not in text
    assert "api_secret" not in text
    assert "secret" not in text
