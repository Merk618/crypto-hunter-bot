"""Dependency wiring tests."""

from app.core.dependencies import (
    dependency_status,
    get_dashboard_service,
    get_paper_broker,
    get_paper_trading_bot,
    get_risk_manager,
    get_trade_executor,
    reset_dependencies,
)


def test_dependencies_share_stateful_paper_broker() -> None:
    """Paper broker is shared by endpoints, executor, and dashboard."""
    reset_dependencies()
    broker = get_paper_broker()

    assert get_paper_broker() is broker
    assert get_trade_executor().paper_broker is broker
    assert get_dashboard_service().paper_broker is broker


def test_dependencies_report_consistent_status() -> None:
    """Dependency status confirms shared service wiring."""
    reset_dependencies()
    status = dependency_status()

    assert status["paper_broker_shared_with_trade_executor"] is True
    assert status["paper_broker_shared_with_dashboard"] is True
    assert status["risk_manager_shared_with_bot"] is True


def test_dependencies_share_risk_manager_with_bot() -> None:
    """The paper bot uses the central risk manager."""
    reset_dependencies()
    assert get_paper_trading_bot().risk_manager is get_risk_manager()
