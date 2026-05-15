"""Application configuration and safety validation."""

from enum import StrEnum
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotMode(StrEnum):
    """Supported bot runtime modes."""

    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class ExchangeName(StrEnum):
    """Supported exchange adapter names."""

    KRAKEN = "kraken"
    COINBASE = "coinbase"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    bot_mode: BotMode = Field(default=BotMode.PAPER, alias="BOT_MODE")
    enable_live_trading: bool = Field(default=False, alias="ENABLE_LIVE_TRADING")
    require_live_confirmation: bool = Field(default=True, alias="REQUIRE_LIVE_CONFIRMATION")
    exchange: ExchangeName = Field(default=ExchangeName.KRAKEN, alias="EXCHANGE")
    base_currency: str = Field(default="USD", alias="BASE_CURRENCY")
    allowed_symbols: list[str] = Field(
        default_factory=lambda: ["BTC/USD", "ETH/USD", "SOL/USD", "SUI/USD", "XRP/USD", "LINK/USD", "AVAX/USD"],
        alias="ALLOWED_SYMBOLS",
    )
    max_risk_per_trade: float = Field(default=0.01, gt=0, le=1, alias="MAX_RISK_PER_TRADE")
    max_daily_loss: float = Field(default=0.03, gt=0, le=1, alias="MAX_DAILY_LOSS")
    max_open_positions: int = Field(default=3, gt=0, alias="MAX_OPEN_POSITIONS")
    max_position_allocation: float = Field(default=0.25, gt=0, le=1, alias="MAX_POSITION_ALLOCATION")
    min_signal_score_to_trade: int = Field(default=80, ge=0, le=100, alias="MIN_SIGNAL_SCORE_TO_TRADE")
    max_spread_bps: float = Field(default=50.0, ge=0, alias="MAX_SPREAD_BPS")
    cooldown_after_loss_minutes: int = Field(default=60, ge=0, alias="COOLDOWN_AFTER_LOSS_MINUTES")
    cooldown_after_trade_minutes: int = Field(default=15, ge=0, alias="COOLDOWN_AFTER_TRADE_MINUTES")
    max_trades_per_day: int = Field(default=10, gt=0, alias="MAX_TRADES_PER_DAY")
    max_consecutive_losses: int = Field(default=3, gt=0, alias="MAX_CONSECUTIVE_LOSSES")
    max_api_failures_before_kill: int = Field(default=5, gt=0, alias="MAX_API_FAILURES_BEFORE_KILL")
    paper_starting_cash: float = Field(default=10000.0, gt=0, alias="PAPER_STARTING_CASH")
    paper_fee_rate: float = Field(default=0.0025, ge=0, le=1, alias="PAPER_FEE_RATE")
    paper_slippage_bps: float = Field(default=10.0, ge=0, alias="PAPER_SLIPPAGE_BPS")
    paper_auto_trading_enabled: bool = Field(default=False, alias="PAPER_AUTO_TRADING_ENABLED")
    bot_scan_timeframe: str = Field(default="1h", alias="BOT_SCAN_TIMEFRAME")
    bot_scan_limit: int = Field(default=250, ge=200, alias="BOT_SCAN_LIMIT")
    bot_max_symbols_per_scan: int = Field(default=10, gt=0, alias="BOT_MAX_SYMBOLS_PER_SCAN")
    bot_min_seconds_between_scans: int = Field(default=60, ge=0, alias="BOT_MIN_SECONDS_BETWEEN_SCANS")
    bot_default_order_reason: str = Field(default="auto paper signal", alias="BOT_DEFAULT_ORDER_REASON")
    paper_allow_autobuy: bool = Field(default=True, alias="PAPER_ALLOW_AUTOBUY")
    paper_allow_autosell: bool = Field(default=False, alias="PAPER_ALLOW_AUTOSELL")
    kraken_api_key: str = Field(default="", alias="KRAKEN_API_KEY")
    kraken_api_secret: str = Field(default="", alias="KRAKEN_API_SECRET")
    coinbase_api_key: str = Field(default="", alias="COINBASE_API_KEY")
    coinbase_api_secret: str = Field(default="", alias="COINBASE_API_SECRET")
    discord_webhook_url: str = Field(default="", alias="DISCORD_WEBHOOK_URL")

    @field_validator("allowed_symbols", mode="before")
    @classmethod
    def parse_allowed_symbols(cls, value: str | list[str]) -> list[str]:
        """Parse comma-delimited symbols from environment variables."""
        if isinstance(value, str):
            return [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
        return [symbol.upper() for symbol in value]

    @field_validator("base_currency")
    @classmethod
    def normalize_base_currency(cls, value: str) -> str:
        """Normalize the configured base currency."""
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("BASE_CURRENCY cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_live_safety(self) -> "Settings":
        """Fail safely when live mode is partially enabled."""
        if self.bot_mode != BotMode.LIVE and self.enable_live_trading:
            raise ValueError("ENABLE_LIVE_TRADING can only be true when BOT_MODE=live")
        return self

    def has_exchange_api_keys(self) -> bool:
        """Return whether the selected exchange has API credentials configured."""
        if self.exchange == ExchangeName.KRAKEN:
            return bool(self.kraken_api_key and self.kraken_api_secret)
        if self.exchange == ExchangeName.COINBASE:
            return bool(self.coinbase_api_key and self.coinbase_api_secret)
        return False

    def live_trading_allowed(self) -> bool:
        """Return True only when every live-trading safety condition is satisfied."""
        return (
            self.bot_mode == BotMode.LIVE
            and self.enable_live_trading
            and not self.require_live_confirmation
            and self.has_exchange_api_keys()
        )


def get_settings() -> Settings:
    """Create a Settings instance for application runtime."""
    return Settings()
