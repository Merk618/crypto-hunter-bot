"""Standalone readiness audit tests."""

from app.audit.standalone_readiness_audit import StandaloneReadinessAudit


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


ROUTES = '"/operator/status" "/reports/system-health"'


def test_standalone_audit_blocks_if_safety_audit_fails() -> None:
    """Safety audit failure blocks readiness."""
    report = StandaloneReadinessAudit().audit(safety_report=safety(passed=False), route_text=ROUTES)

    assert report["readiness_status"] == "BLOCKED"


def test_standalone_audit_blocks_if_live_trading_unlocked() -> None:
    """Unlocked live trading blocks readiness."""
    report = StandaloneReadinessAudit().audit(safety_report=safety(live_trading_locked=False), route_text=ROUTES)

    assert report["readiness_status"] == "BLOCKED"


def test_standalone_audit_blocks_if_forbidden_live_order_detected() -> None:
    """Forbidden live order token blocks readiness."""
    report = StandaloneReadinessAudit().audit(safety_report=safety(no_add_order_detected=False), route_text=ROUTES)

    assert report["readiness_status"] == "BLOCKED"


def test_standalone_audit_blocks_if_real_execution_route_detected() -> None:
    """Real execution surface blocks readiness."""
    report = StandaloneReadinessAudit().audit(safety_report=safety(), route_text='"/operator/status" "/reports/system-health" "/live"')

    assert report["readiness_status"] == "BLOCKED"


def test_standalone_audit_ready_for_final_runbook_when_safe() -> None:
    """Safe core state reaches final runbook status."""
    report = StandaloneReadinessAudit().audit(safety_report=safety(), route_text=ROUTES)

    assert report["readiness_status"] == "READY_FOR_FINAL_RUNBOOK"
    assert report["ready_for_v1_freeze"] is False
    assert report["paper_trading_disabled"] is True
    assert report["live_trading_locked"] is True
