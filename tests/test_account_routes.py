"""Account route tests."""


def test_account_routes_exist() -> None:
    """Account routes are registered."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/account/status" in paths
    assert "/account/balances" in paths
    assert "/account/summary" in paths


def test_account_routes_return_disabled_response_by_default() -> None:
    """Account service default is disabled."""
    from app.api.routes import account_summary

    summary = account_summary()
    assert summary["private_read_enabled"] is False
    assert summary["balances"] == []


def test_no_order_placement_methods_added_to_private_client() -> None:
    """Private client exposes no trading or withdrawal methods."""
    from app.exchanges.kraken_private_client import KrakenPrivateClient

    names = {name.lower() for name in dir(KrakenPrivateClient)}
    assert not any(name in names for name in {"place_order", "add_order", "cancel_order", "withdraw", "transfer"})


def test_no_live_trading_or_withdrawal_routes_exist() -> None:
    """No live or withdrawal routes exist."""
    from app.main import app

    paths = {route.path.lower() for route in app.routes}
    assert not any(path.startswith("/live") for path in paths)
    assert not any("withdraw" in path for path in paths)
