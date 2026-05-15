"""Shared dependency wiring for Crypto Hunter services."""

from __future__ import annotations

from app.account.account_service import AccountService
from app.bot.paper_trading_bot import PaperTradingBot
from app.config import Settings, get_settings
from app.data.market_data_service import MarketDataService
from app.execution.dry_run_executor import DryRunExecutor
from app.execution.emergency_controls import EmergencyControls
from app.execution.execution_guard import ExecutionGuard
from app.execution.order_validator import OrderValidator
from app.execution.paper_broker import PaperBroker
from app.execution.trade_executor import TradeExecutor
from app.reporting.dashboard_service import DashboardService
from app.risk.cooldown_manager import CooldownManager
from app.risk.kill_switch import KillSwitch
from app.risk.risk_manager import RiskManager
from app.storage.trade_journal import TradeJournal
from app.strategies.crypto_hunter_strategy import CryptoHunterStrategy

_services: dict[str, object] = {}


def reset_dependencies() -> None:
    """Clear shared services for tests or controlled app resets."""
    _services.clear()


def get_config() -> Settings:
    """Return runtime settings."""
    if "settings" not in _services:
        _services["settings"] = get_settings()
    return _services["settings"]  # type: ignore[return-value]


def get_market_data_service() -> MarketDataService:
    """Return shared market data service."""
    if "market_data_service" not in _services:
        _services["market_data_service"] = MarketDataService(settings=get_config())
    return _services["market_data_service"]  # type: ignore[return-value]


def get_strategy() -> CryptoHunterStrategy:
    """Return shared strategy service."""
    if "strategy" not in _services:
        _services["strategy"] = CryptoHunterStrategy()
    return _services["strategy"]  # type: ignore[return-value]


def get_paper_broker() -> PaperBroker:
    """Return shared paper broker so endpoint state is consistent."""
    if "paper_broker" not in _services:
        _services["paper_broker"] = PaperBroker(settings=get_config(), journal=get_trade_journal())
    return _services["paper_broker"]  # type: ignore[return-value]


def get_trade_executor() -> TradeExecutor:
    """Return shared trade executor backed by the shared paper broker."""
    if "trade_executor" not in _services:
        _services["trade_executor"] = TradeExecutor(settings=get_config(), paper_broker=get_paper_broker())
    return _services["trade_executor"]  # type: ignore[return-value]


def get_kill_switch() -> KillSwitch:
    """Return shared kill switch."""
    if "kill_switch" not in _services:
        _services["kill_switch"] = KillSwitch(max_api_failures_before_kill=get_config().max_api_failures_before_kill)
    return _services["kill_switch"]  # type: ignore[return-value]


def get_cooldown_manager() -> CooldownManager:
    """Return shared cooldown manager."""
    if "cooldown_manager" not in _services:
        settings = get_config()
        _services["cooldown_manager"] = CooldownManager(
            after_trade_minutes=settings.cooldown_after_trade_minutes,
            after_loss_minutes=settings.cooldown_after_loss_minutes,
        )
    return _services["cooldown_manager"]  # type: ignore[return-value]


def get_risk_manager() -> RiskManager:
    """Return shared risk manager."""
    if "risk_manager" not in _services:
        _services["risk_manager"] = RiskManager(settings=get_config(), kill_switch=get_kill_switch(), cooldown_manager=get_cooldown_manager())
    return _services["risk_manager"]  # type: ignore[return-value]


def get_trade_journal() -> TradeJournal:
    """Return shared trade journal."""
    if "trade_journal" not in _services:
        _services["trade_journal"] = TradeJournal()
    return _services["trade_journal"]  # type: ignore[return-value]


def get_paper_trading_bot() -> PaperTradingBot:
    """Return shared paper trading bot wired to shared stateful services."""
    if "paper_trading_bot" not in _services:
        _services["paper_trading_bot"] = PaperTradingBot(
            market_data_service=get_market_data_service(),
            strategy=get_strategy(),
            risk_manager=get_risk_manager(),
            trade_executor=get_trade_executor(),
            settings=get_config(),
            journal=get_trade_journal(),
        )
    return _services["paper_trading_bot"]  # type: ignore[return-value]


def get_account_service() -> AccountService:
    """Return shared read-only account service."""
    if "account_service" not in _services:
        _services["account_service"] = AccountService(settings=get_config(), journal=get_trade_journal())
    return _services["account_service"]  # type: ignore[return-value]


def get_dashboard_service() -> DashboardService:
    """Return shared dashboard reporting service."""
    if "dashboard_service" not in _services:
        bot = get_paper_trading_bot()
        _services["dashboard_service"] = DashboardService(
            bot_state=bot.state,
            paper_broker=get_paper_broker(),
            risk_manager=get_risk_manager(),
            trade_journal=get_trade_journal(),
        )
    return _services["dashboard_service"]  # type: ignore[return-value]


def get_order_validator() -> OrderValidator:
    """Return shared order validator."""
    if "order_validator" not in _services:
        _services["order_validator"] = OrderValidator(settings=get_config())
    return _services["order_validator"]  # type: ignore[return-value]


def get_dry_run_executor() -> DryRunExecutor:
    """Return shared dry-run executor."""
    if "dry_run_executor" not in _services:
        _services["dry_run_executor"] = DryRunExecutor(settings=get_config(), journal=get_trade_journal())
    return _services["dry_run_executor"]  # type: ignore[return-value]


def get_execution_guard() -> ExecutionGuard:
    """Return shared execution guard."""
    if "execution_guard" not in _services:
        _services["execution_guard"] = ExecutionGuard(settings=get_config())
    return _services["execution_guard"]  # type: ignore[return-value]


def get_emergency_controls() -> EmergencyControls:
    """Return shared emergency controls."""
    if "emergency_controls" not in _services:
        _services["emergency_controls"] = EmergencyControls(
            bot_state=get_paper_trading_bot().state,
            paper_broker=get_paper_broker(),
            settings=get_config(),
        )
    return _services["emergency_controls"]  # type: ignore[return-value]


def dependency_status() -> dict:
    """Return service identity and consistency information without secrets."""
    broker = get_paper_broker()
    executor = get_trade_executor()
    bot = get_paper_trading_bot()
    dashboard = get_dashboard_service()
    return {
        "paper_broker_shared_with_trade_executor": executor.paper_broker is broker,
        "paper_broker_shared_with_dashboard": dashboard.paper_broker is broker,
        "risk_manager_shared_with_bot": bot.risk_manager is get_risk_manager(),
        "journal_enabled": get_config().enable_trade_journal,
        "services_initialized": sorted(_services.keys()),
    }
