"""Phase 43 v1 freeze report tests."""

from app.audit.v1_freeze_report import V1FreezeReportService


def test_v1_freeze_report_disables_paper_and_live_trading() -> None:
    """Freeze report keeps paper and live trading disabled."""
    report = V1FreezeReportService().freeze_report()

    assert report["paper_trading_enabled"] is False
    assert report["live_trading_enabled"] is False
    assert report["controlled_paper_enabled"] is False


def test_v1_freeze_report_safety_surfaces_are_clean() -> None:
    """Freeze report confirms final execution surfaces are absent."""
    report = V1FreezeReportService().freeze_report()

    assert report["add_order_absent"] is True
    assert report["real_execution_absent"] is True
    assert report["observation_system_available"] is True
    assert report["signal_quality_available"] is True
    assert report["strategy_checkpoint_available"] is True


def test_handoff_package_includes_operator_commands() -> None:
    """Handoff package includes startup, test, and health commands."""
    package = V1FreezeReportService().handoff_package()

    assert "uvicorn" in package["startup_command"]
    assert "pytest" in package["test_command"]
    assert "health_check_phase42.py" in package["health_check_command"]
    assert package["recommended_github_tag"] == "v1.0.0-standalone-observation"


def test_future_roadmap_includes_separate_stock_trader_bot() -> None:
    """Future roadmap points to a separate Stock Trader Bot project."""
    roadmap = V1FreezeReportService().future_roadmap()

    assert "Standalone MooMoo Stock Trader Bot" == roadmap["next_project"]
    assert any("separate repo" in item.lower() for item in roadmap["stock_trader_bot"])

