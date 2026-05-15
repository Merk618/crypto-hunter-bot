"""Reporting route tests."""


def test_report_endpoints_exist() -> None:
    """Report routes are registered."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/reports/overview" in paths
    assert "/reports/paper-performance" in paths
    assert "/reports/signal-performance" in paths
    assert "/reports/risk-summary" in paths
    assert "/reports/recent-activity" in paths
    assert "/reports/equity-curve" in paths
    assert "/reports/full-dashboard" in paths


def test_report_endpoints_are_read_only_and_do_not_execute_trades() -> None:
    """Reporting routes are not order routes."""
    from app.main import app

    report_paths = [route.path for route in app.routes if route.path.startswith("/reports")]
    assert report_paths
    assert not any("order" in path or "scan-once" in path or "start" in path for path in report_paths)


def test_reports_do_not_expose_api_secrets() -> None:
    """Route names do not expose secrets."""
    from app.main import app

    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/reports"))
    assert "secret" not in paths
    assert "api_key" not in paths


def test_no_live_trading_or_withdrawal_routes_exist() -> None:
    """No live or withdrawal routes exist."""
    from app.main import app

    paths = {route.path.lower() for route in app.routes}
    assert not any(path.startswith("/live") for path in paths)
    assert not any("withdraw" in path for path in paths)
