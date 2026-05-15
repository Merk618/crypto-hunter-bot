"""Phase 13 integration regression tests."""

from app.api import routes
from app.core.dependencies import get_paper_trading_bot, reset_dependencies
from app.main import app


def setup_function() -> None:
    """Reset shared services before each integration test."""
    reset_dependencies()


def test_paper_order_state_persists_across_endpoint_calls() -> None:
    """Paper order changes account state and subsequent reads see it."""
    routes.paper_reset()
    before = routes.paper_account()
    result = routes.paper_order(
        routes.PaperOrderRequest(symbol="BTC/USD", side="buy", quantity=0.01, market_price=1000, reason="integration paper buy")
    )
    after = routes.paper_account()

    assert result["accepted"] is True
    assert after["cash_balance"] < before["cash_balance"]
    assert after["open_positions"] == 1


def test_dashboard_reporting_sees_paper_account_state() -> None:
    """Reporting uses the same paper broker state as paper endpoints."""
    routes.paper_reset()
    routes.paper_order(routes.PaperOrderRequest(symbol="ETH/USD", side="buy", quantity=0.02, market_price=1000))
    account = routes.paper_account()
    report = routes.report_paper_performance()

    assert report["cash_balance"] == account["cash_balance"]
    assert report["open_positions"] == account["open_positions"]


def test_bot_start_manual_starts_only_paper_bot() -> None:
    """Manual start starts the paper bot without live mode."""
    response = routes.bot_start(routes.BotStartRequest(manual_start=True))

    assert response["is_running"] is True
    assert response["mode"] == "paper"


def test_bot_scan_once_remains_paper_only(monkeypatch) -> None:
    """Manual scan endpoint does not place real exchange orders."""
    bot = get_paper_trading_bot()
    monkeypatch.setattr(bot, "run_watchlist_scan", lambda: [])
    routes.bot_start(routes.BotStartRequest(manual_start=True))

    result = routes.bot_scan_once()

    assert result["trades_executed"] == 0
    assert result["symbols_scanned"] == 0


def test_execution_dry_run_order_remains_dry_run_only() -> None:
    """Dry-run execution returns preview only."""
    response = routes.execution_dry_run_order(
        routes.ExecutionOrderRequest(
            symbol="BTC/USD",
            side="buy",
            order_type="market",
            quantity=0.001,
            estimated_price=65000,
            reason="integration dry run",
            signal_score=84,
            signal_category="STRONG_BUY",
            risk_approved=True,
            account_summary={"cash_balance": 1000},
            ticker={"bid": 64990, "ask": 65010, "timestamp": "2999-01-01T00:00:00+00:00"},
        )
    )

    assert response["status"] == "DRY_RUN"
    assert response["approved"] is True


def test_execution_safety_status_confirms_live_trading_blocked() -> None:
    """Safety status should report live execution blocked."""
    status = routes.execution_safety_status()

    assert status["can_execute_live_order"] is False


def test_account_status_does_not_expose_secrets() -> None:
    """Account status endpoint must not leak credentials."""
    text = str(routes.account_status()).lower()

    assert "api_key" not in text
    assert "api_secret" not in text
    assert "secret" not in text


def test_full_dashboard_does_not_expose_secrets() -> None:
    """Full dashboard is safe for frontend use."""
    text = str(routes.report_full_dashboard()).lower()

    assert "api_key" not in text
    assert "api_secret" not in text
    assert "secret" not in text


def test_journal_routes_work_after_creating_paper_order() -> None:
    """Journal routes can read paper order records."""
    routes.journal_init()
    routes.paper_reset()
    routes.paper_order(routes.PaperOrderRequest(symbol="SOL/USD", side="buy", quantity=1, market_price=10))
    orders = routes.journal_orders(limit=5)

    assert "orders" in orders
    assert isinstance(orders["orders"], list)


def test_system_routes_exist_and_safety_audit_passes() -> None:
    """System endpoints are registered and safe by default."""
    paths = {route.path for route in app.routes}

    assert "/system/runtime" in paths
    assert "/system/dependencies" in paths
    assert "/system/safety-audit" in paths
    assert routes.system_runtime()["bot_mode"] == "paper"
    assert routes.system_dependencies()["paper_broker_shared_with_trade_executor"] is True
    assert routes.system_safety_audit()["passed"] is True
