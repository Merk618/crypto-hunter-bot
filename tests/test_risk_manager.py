"""Risk manager tests."""

from app.config import Settings
from app.risk.cooldown_manager import CooldownManager
from app.risk.kill_switch import KillSwitch
from app.risk.risk_manager import RiskManager


def settings() -> Settings:
    """Return deterministic risk settings."""
    return Settings(_env_file=None)


def signal(score: int = 84, category: str = "STRONG_BUY", blockers=None, stop: float = 90.0) -> dict:
    """Build a synthetic signal."""
    return {
        "score": score,
        "category": category,
        "blockers": blockers or [],
        "suggested_stop_loss": stop,
        "suggested_entry": 100.0,
    }


def account(**overrides) -> dict:
    """Build synthetic account summary."""
    base = {
        "equity": 10000.0,
        "cash_balance": 10000.0,
        "realized_pnl": 0.0,
        "fills": 0,
        "trades_today": 0,
        "consecutive_losses": 0,
    }
    base.update(overrides)
    return base


def position(symbol: str = "BTC/USD", quantity: float = 1.0, market_value: float = 100.0) -> dict:
    """Build synthetic position."""
    return {"symbol": symbol, "quantity": quantity, "market_value": market_value}


def manager(kill_switch=None, cooldown_manager=None) -> RiskManager:
    """Build a risk manager."""
    return RiskManager(settings=settings(), kill_switch=kill_switch, cooldown_manager=cooldown_manager)


def test_risk_manager_rejects_low_signal_score() -> None:
    """Low signal score blocks trade."""
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(score=70), account(), [], 100)
    assert decision.approved is False
    assert "signal score below minimum" in decision.blockers


def test_risk_manager_rejects_signal_blockers() -> None:
    """Signal blockers block trade."""
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(blockers=["RSI >= 75"]), account(), [], 100)
    assert decision.approved is False
    assert "signal blocker: RSI >= 75" in decision.blockers


def test_risk_manager_rejects_too_many_open_positions() -> None:
    """Max open positions blocks new symbols."""
    positions = [position("ETH/USD"), position("SOL/USD"), position("XRP/USD")]
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(), account(), positions, 100)
    assert decision.approved is False
    assert "max open positions reached" in decision.blockers


def test_risk_manager_allows_adding_to_existing_position_if_allocation_allows() -> None:
    """Existing positions bypass max count when allocation allows."""
    positions = [position("BTC/USD", market_value=100), position("ETH/USD"), position("SOL/USD")]
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(), account(), positions, 100)
    assert decision.approved is True
    assert decision.approved_quantity is not None


def test_risk_manager_rejects_oversized_allocation() -> None:
    """Explicit oversized quantity is rejected."""
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(), account(), [], 100, requested_quantity=100)
    assert decision.approved is False
    assert "requested quantity exceeds maximum allowed by risk, cash, or allocation" in decision.blockers


def test_risk_manager_rejects_high_spread() -> None:
    """High spread blocks trade."""
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(), account(), [], 100, spread_bps=100)
    assert decision.approved is False
    assert "spread exceeds maximum" in decision.blockers


def test_risk_manager_rejects_daily_loss_limit_exceeded() -> None:
    """Daily realized loss blocks trade."""
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(), account(realized_pnl=-400), [], 100)
    assert decision.approved is False
    assert "daily realized loss limit exceeded" in decision.blockers


def test_risk_manager_rejects_when_kill_switch_active() -> None:
    """Active kill switch blocks trade."""
    kill = KillSwitch()
    kill.activate("test")
    decision = manager(kill_switch=kill).evaluate_trade("BTC/USD", "buy", signal(), account(), [], 100)
    assert decision.approved is False
    assert "kill switch is active" in decision.blockers


def test_risk_manager_rejects_when_symbol_cooldown_active() -> None:
    """Active symbol cooldown blocks trade."""
    cooldown = CooldownManager()
    cooldown.set_symbol_cooldown("BTC/USD", 10, "test")
    decision = manager(cooldown_manager=cooldown).evaluate_trade("BTC/USD", "buy", signal(), account(), [], 100)
    assert decision.approved is False
    assert "symbol cooldown is active" in decision.blockers


def test_risk_manager_rejects_max_trades_per_day_exceeded() -> None:
    """Max trades per day blocks trade."""
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(), account(trades_today=10), [], 100)
    assert decision.approved is False
    assert "max trades per day exceeded" in decision.blockers


def test_risk_manager_rejects_consecutive_loss_limit_exceeded() -> None:
    """Consecutive loss limit blocks trade."""
    decision = manager().evaluate_trade("BTC/USD", "buy", signal(), account(consecutive_losses=3), [], 100)
    assert decision.approved is False
    assert "consecutive loss limit exceeded" in decision.blockers


def test_risk_manager_sell_allows_existing_position_reduction() -> None:
    """Sell approval only reduces existing positions."""
    decision = manager().evaluate_trade("BTC/USD", "sell", signal(), account(), [position(quantity=1.0)], 100, requested_quantity=0.5, manual_override=True)
    assert decision.approved is True
    assert decision.approved_quantity == 0.5


def test_fastapi_risk_routes_exist() -> None:
    """Risk routes are registered."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/risk/status" in paths
    assert "/risk/evaluate" in paths
    assert "/risk/kill-switch/activate" in paths
    assert "/risk/kill-switch/deactivate" in paths


def test_no_live_trading_or_withdrawal_routes_exist() -> None:
    """No live trading or withdrawal routes exist."""
    from app.main import app

    paths = {route.path.lower() for route in app.routes}
    assert not any(path.startswith("/live") for path in paths)
    assert not any("withdraw" in path for path in paths)
