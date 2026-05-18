"""Controlled paper audit tests."""

from app.config import Settings
from app.observation.controlled_paper_audit import ControlledPaperAuditService


def settings(**updates):
    """Build settings overrides."""
    return Settings(_env_file=None).model_copy(update=updates)


def trade(**kwargs):
    """Build controlled paper trade result."""
    data = {"mode": "CONTROLLED_PAPER_OBSERVATION", "broker": "PAPER", "real_execution": False, "live_trade": False}
    data.update(kwargs)
    return data


def run(**kwargs):
    """Build controlled paper run."""
    data = {
        "run_id": "run-1",
        "status": "PAPER_OBSERVATION_RUN_COMPLETED",
        "paper_trade_previews_created": 1,
        "paper_trades_created": 0,
        "trade_results": [],
    }
    data.update(kwargs)
    return data


def test_audit_passes_when_disabled_and_no_trades() -> None:
    """Default disabled config passes audit."""
    report = ControlledPaperAuditService().audit([])

    assert report["passed"] is True
    assert report["controlled_paper_enabled"] is False


def test_audit_fails_if_controlled_mode_enabled_by_default() -> None:
    """Enabled controlled paper config fails default audit."""
    report = ControlledPaperAuditService(settings=settings(controlled_paper_observation_enabled=True)).audit([])

    assert report["passed"] is False


def test_audit_fails_if_buys_allowed_by_default() -> None:
    """Buy allowance fails audit."""
    report = ControlledPaperAuditService(settings=settings(controlled_paper_observation_allow_buys=True)).audit([])

    assert report["passed"] is False


def test_audit_fails_if_sells_allowed_by_default() -> None:
    """Sell allowance fails audit."""
    report = ControlledPaperAuditService(settings=settings(controlled_paper_observation_allow_sells=True)).audit([])

    assert report["passed"] is False


def test_audit_fails_if_live_trade_detected() -> None:
    """Live trade labels fail audit."""
    report = ControlledPaperAuditService().audit([run(trade_results=[trade(live_trade=True)])])

    assert report["passed"] is False
    assert report["live_trades_detected"] == 1


def test_audit_fails_if_real_execution_detected() -> None:
    """Real execution labels fail audit."""
    report = ControlledPaperAuditService().audit([run(trade_results=[trade(real_execution=True)])])

    assert report["passed"] is False
    assert report["real_execution_detected"] == 1


def test_audit_fails_if_broker_not_paper() -> None:
    """Non-paper broker fails audit."""
    report = ControlledPaperAuditService().audit([run(trade_results=[trade(broker="LIVE")])])

    assert report["passed"] is False
    assert report["non_paper_broker_detected"] == 1


def test_audit_fails_if_preview_created_trades() -> None:
    """Preview-only records must not create trades."""
    report = ControlledPaperAuditService().audit([run(status="PREVIEW_ONLY", paper_trades_created=1, trade_results=[trade()])])

    assert report["passed"] is False
    assert report["preview_created_trades"] == 1


def test_audit_fails_if_disabled_run_created_trades() -> None:
    """Disabled run records must not create trades."""
    report = ControlledPaperAuditService().audit([run(status="DISABLED_BY_CONFIG", paper_trades_created=1, trade_results=[trade()])])

    assert report["passed"] is False
    assert report["disabled_run_created_trades"] == 1


def test_audit_validates_controlled_mode_and_paper_broker_labels() -> None:
    """Valid controlled paper labels pass."""
    report = ControlledPaperAuditService().audit([run(paper_trades_created=1, trade_results=[trade()])])

    assert report["paper_only_labels_valid"] is True
    assert report["non_paper_broker_detected"] == 0
