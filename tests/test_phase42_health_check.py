"""Phase 42 health check tests."""

from app.operator.local_runbook import LocalOperatorRunbookService


def test_health_check_reports_safety_audit() -> None:
    """Health check reports safety audit."""
    report = LocalOperatorRunbookService().one_command_health_check()
    names = {check["name"] for check in report["checks"]}

    assert "safety_audit" in names


def test_health_check_reports_live_locked_and_forbidden_token_absent() -> None:
    """Health check reports live lock and forbidden token absence."""
    report = LocalOperatorRunbookService().one_command_health_check()
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["live_trading_locked"]["passed"] is True
    assert checks["forbidden_live_order_absent"]["passed"] is True


def test_health_check_reports_paper_trading_disabled() -> None:
    """Health check reports paper trading disabled."""
    report = LocalOperatorRunbookService().one_command_health_check()
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["paper_trading_disabled"]["passed"] is True


def test_health_check_reports_no_secrets_exposed() -> None:
    """Health check reports no secrets exposed."""
    report = LocalOperatorRunbookService().one_command_health_check()
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["secrets_not_exposed"]["passed"] is True
