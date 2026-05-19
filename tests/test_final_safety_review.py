"""Final safety review tests."""

from app.audit.final_safety_review import FinalSafetyReview
from app.config import Settings


def safety(**updates):
    """Build safety report."""
    data = {
        "passed": True,
        "live_trading_locked": True,
        "no_add_order_detected": True,
        "secrets_not_exposed": True,
        "dangerous_config_detected": False,
    }
    data.update(updates)
    return data


def test_final_safety_detects_dangerous_config() -> None:
    """Dangerous config is detected."""
    settings = Settings(_env_file=None).model_copy(update={"enable_live_trading": True})
    report = FinalSafetyReview(settings=settings).review(safety_report=safety(), executable_text="", route_text="")

    assert report["dangerous_config_detected"] is True
    assert report["passed"] is False


def test_final_safety_detects_withdrawal_style_methods() -> None:
    """Withdrawal-style methods are detected."""
    report = FinalSafetyReview().review(safety_report=safety(), executable_text="def withdraw(): pass", route_text="")

    assert report["withdrawal_methods_absent"] is False
    assert report["passed"] is False


def test_final_safety_detects_secret_exposure_failure() -> None:
    """Secret exposure failure blocks."""
    report = FinalSafetyReview().review(safety_report=safety(secrets_not_exposed=False), executable_text="", route_text="")

    assert report["secrets_not_exposed"] is False
    assert report["passed"] is False


def test_final_safety_detects_moomoo_execution_methods() -> None:
    """MooMoo execution methods are detected."""
    report = FinalSafetyReview().review(safety_report=safety(), executable_text="def unlock_trade(): pass", route_text="")

    assert report["moomoo_execution_absent"] is False
    assert report["passed"] is False
