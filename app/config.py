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
    database_url: str = Field(default="sqlite:///./crypto_hunter.db", alias="DATABASE_URL")
    enable_trade_journal: bool = Field(default=True, alias="ENABLE_TRADE_JOURNAL")
    backtest_starting_cash: float = Field(default=10000.0, gt=0, alias="BACKTEST_STARTING_CASH")
    backtest_fee_rate: float = Field(default=0.0025, ge=0, le=1, alias="BACKTEST_FEE_RATE")
    backtest_slippage_bps: float = Field(default=10.0, ge=0, alias="BACKTEST_SLIPPAGE_BPS")
    backtest_default_timeframe: str = Field(default="1h", alias="BACKTEST_DEFAULT_TIMEFRAME")
    backtest_min_signal_score: int = Field(default=80, ge=0, le=100, alias="BACKTEST_MIN_SIGNAL_SCORE")
    backtest_allow_shorts: bool = Field(default=False, alias="BACKTEST_ALLOW_SHORTS")
    backtest_max_open_positions: int = Field(default=3, gt=0, alias="BACKTEST_MAX_OPEN_POSITIONS")
    kraken_api_key: str = Field(default="", alias="KRAKEN_API_KEY")
    kraken_api_secret: str = Field(default="", alias="KRAKEN_API_SECRET")
    kraken_private_read_enabled: bool = Field(default=False, alias="KRAKEN_PRIVATE_READ_ENABLED")
    kraken_private_trading_enabled: bool = Field(default=False, alias="KRAKEN_PRIVATE_TRADING_ENABLED")
    kraken_require_read_only: bool = Field(default=True, alias="KRAKEN_REQUIRE_READ_ONLY")
    kraken_account_cache_seconds: int = Field(default=30, ge=0, alias="KRAKEN_ACCOUNT_CACHE_SECONDS")
    live_trading_gate_enabled: bool = Field(default=False, alias="LIVE_TRADING_GATE_ENABLED")
    dry_run_execution_enabled: bool = Field(default=True, alias="DRY_RUN_EXECUTION_ENABLED")
    require_risk_approval_for_orders: bool = Field(default=True, alias="REQUIRE_RISK_APPROVAL_FOR_ORDERS")
    require_account_balance_check: bool = Field(default=True, alias="REQUIRE_ACCOUNT_BALANCE_CHECK")
    require_spread_check: bool = Field(default=True, alias="REQUIRE_SPREAD_CHECK")
    require_market_data_freshness: bool = Field(default=True, alias="REQUIRE_MARKET_DATA_FRESHNESS")
    max_order_notional_usd: float = Field(default=100.0, gt=0, alias="MAX_ORDER_NOTIONAL_USD")
    min_order_notional_usd: float = Field(default=5.0, gt=0, alias="MIN_ORDER_NOTIONAL_USD")
    max_allowed_slippage_bps: float = Field(default=50.0, ge=0, alias="MAX_ALLOWED_SLIPPAGE_BPS")
    market_data_stale_seconds: int = Field(default=30, ge=0, alias="MARKET_DATA_STALE_SECONDS")
    emergency_cancel_enabled: bool = Field(default=False, alias="EMERGENCY_CANCEL_ENABLED")
    dead_man_switch_enabled: bool = Field(default=False, alias="DEAD_MAN_SWITCH_ENABLED")
    dead_man_switch_timeout_seconds: int = Field(default=60, ge=0, alias="DEAD_MAN_SWITCH_TIMEOUT_SECONDS")
    phase14_smoke_symbols: list[str] = Field(default_factory=lambda: ["BTC/USD", "ETH/USD", "SOL/USD", "SUI/USD"], alias="PHASE14_SMOKE_SYMBOLS")
    phase14_timeframe: str = Field(default="1h", alias="PHASE14_TIMEFRAME")
    phase14_candle_limit: int = Field(default=250, ge=200, alias="PHASE14_CANDLE_LIMIT")
    phase14_allow_paper_scan: bool = Field(default=False, alias="PHASE14_ALLOW_PAPER_SCAN")
    moomoo_enabled: bool = Field(default=False, alias="MOOMOO_ENABLED")
    moomoo_opend_host: str = Field(default="127.0.0.1", alias="MOOMOO_OPEND_HOST")
    moomoo_opend_port: int = Field(default=11111, gt=0, le=65535, alias="MOOMOO_OPEND_PORT")
    moomoo_read_only: bool = Field(default=True, alias="MOOMOO_READ_ONLY")
    moomoo_trading_enabled: bool = Field(default=False, alias="MOOMOO_TRADING_ENABLED")
    moomoo_paper_trading_enabled: bool = Field(default=False, alias="MOOMOO_PAPER_TRADING_ENABLED")
    moomoo_unlock_trade_context: bool = Field(default=False, alias="MOOMOO_UNLOCK_TRADE_CONTEXT")
    moomoo_account_id: str = Field(default="", alias="MOOMOO_ACCOUNT_ID")
    moomoo_market_region: str = Field(default="US", alias="MOOMOO_MARKET_REGION")
    moomoo_candle_limit_default: int = Field(default=250, gt=0, alias="MOOMOO_CANDLE_LIMIT_DEFAULT")
    moomoo_quote_timeout_seconds: int = Field(default=10, gt=0, alias="MOOMOO_QUOTE_TIMEOUT_SECONDS")
    stock_hunter_enabled: bool = Field(default=False, alias="STOCK_HUNTER_ENABLED")
    stock_hunter_default_symbols: list[str] = Field(default_factory=lambda: ["AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "TSLA"], alias="STOCK_HUNTER_DEFAULT_SYMBOLS")
    stock_hunter_enable_options_analysis: bool = Field(default=True, alias="STOCK_HUNTER_ENABLE_OPTIONS_ANALYSIS")
    stock_hunter_min_option_volume: int = Field(default=500, ge=0, alias="STOCK_HUNTER_MIN_OPTION_VOLUME")
    stock_hunter_min_option_open_interest: int = Field(default=1000, ge=0, alias="STOCK_HUNTER_MIN_OPTION_OPEN_INTEREST")
    stock_hunter_max_bid_ask_spread_pct: float = Field(default=8.0, ge=0, alias="STOCK_HUNTER_MAX_BID_ASK_SPREAD_PCT")
    stock_hunter_target_delta_min: float = Field(default=0.50, ge=0, le=1, alias="STOCK_HUNTER_TARGET_DELTA_MIN")
    stock_hunter_target_delta_max: float = Field(default=0.60, ge=0, le=1, alias="STOCK_HUNTER_TARGET_DELTA_MAX")
    stock_hunter_allow_trading: bool = Field(default=False, alias="STOCK_HUNTER_ALLOW_TRADING")
    stock_hunter_read_only: bool = Field(default=True, alias="STOCK_HUNTER_READ_ONLY")
    stock_hunter_min_stock_score: int = Field(default=65, ge=0, le=100, alias="STOCK_HUNTER_MIN_STOCK_SCORE")
    stock_hunter_strong_score: int = Field(default=80, ge=0, le=100, alias="STOCK_HUNTER_STRONG_SCORE")
    stock_hunter_require_market_open: bool = Field(default=False, alias="STOCK_HUNTER_REQUIRE_MARKET_OPEN")
    stock_hunter_min_avg_volume: int = Field(default=500000, ge=0, alias="STOCK_HUNTER_MIN_AVG_VOLUME")
    stock_hunter_max_extended_rsi: float = Field(default=75.0, ge=0, le=100, alias="STOCK_HUNTER_MAX_EXTENDED_RSI")
    stock_hunter_ideal_rsi_min: float = Field(default=40.0, ge=0, le=100, alias="STOCK_HUNTER_IDEAL_RSI_MIN")
    stock_hunter_ideal_rsi_max: float = Field(default=65.0, ge=0, le=100, alias="STOCK_HUNTER_IDEAL_RSI_MAX")
    stock_hunter_options_min_dte: int = Field(default=14, ge=0, alias="STOCK_HUNTER_OPTIONS_MIN_DTE")
    stock_hunter_options_max_dte: int = Field(default=90, ge=0, alias="STOCK_HUNTER_OPTIONS_MAX_DTE")
    stock_hunter_options_target_dte_min: int = Field(default=21, ge=0, alias="STOCK_HUNTER_OPTIONS_TARGET_DTE_MIN")
    stock_hunter_options_target_dte_max: int = Field(default=60, ge=0, alias="STOCK_HUNTER_OPTIONS_TARGET_DTE_MAX")
    options_scanner_enabled: bool = Field(default=False, alias="OPTIONS_SCANNER_ENABLED")
    options_scanner_read_only: bool = Field(default=True, alias="OPTIONS_SCANNER_READ_ONLY")
    options_scanner_allow_execution: bool = Field(default=False, alias="OPTIONS_SCANNER_ALLOW_EXECUTION")
    options_scanner_min_volume: int = Field(default=500, ge=0, alias="OPTIONS_SCANNER_MIN_VOLUME")
    options_scanner_min_open_interest: int = Field(default=1000, ge=0, alias="OPTIONS_SCANNER_MIN_OPEN_INTEREST")
    options_scanner_max_spread_pct: float = Field(default=8.0, ge=0, alias="OPTIONS_SCANNER_MAX_SPREAD_PCT")
    options_scanner_target_delta_min: float = Field(default=0.50, ge=0, le=1, alias="OPTIONS_SCANNER_TARGET_DELTA_MIN")
    options_scanner_target_delta_max: float = Field(default=0.60, ge=0, le=1, alias="OPTIONS_SCANNER_TARGET_DELTA_MAX")
    options_scanner_min_dte: int = Field(default=14, ge=0, alias="OPTIONS_SCANNER_MIN_DTE")
    options_scanner_max_dte: int = Field(default=90, ge=0, alias="OPTIONS_SCANNER_MAX_DTE")
    options_scanner_target_dte_min: int = Field(default=21, ge=0, alias="OPTIONS_SCANNER_TARGET_DTE_MIN")
    options_scanner_target_dte_max: int = Field(default=60, ge=0, alias="OPTIONS_SCANNER_TARGET_DTE_MAX")
    options_scanner_max_iv_rank_warning: float = Field(default=70.0, ge=0, le=100, alias="OPTIONS_SCANNER_MAX_IV_RANK_WARNING")
    options_scanner_min_underlying_score: int = Field(default=65, ge=0, le=100, alias="OPTIONS_SCANNER_MIN_UNDERLYING_SCORE")
    options_scanner_top_n: int = Field(default=10, ge=1, alias="OPTIONS_SCANNER_TOP_N")
    alerts_enabled: bool = Field(default=False, alias="ALERTS_ENABLED")
    alerts_read_only: bool = Field(default=True, alias="ALERTS_READ_ONLY")
    alert_channel_console: bool = Field(default=True, alias="ALERT_CHANNEL_CONSOLE")
    alert_channel_discord: bool = Field(default=False, alias="ALERT_CHANNEL_DISCORD")
    alert_channel_email: bool = Field(default=False, alias="ALERT_CHANNEL_EMAIL")
    alert_min_crypto_score: int = Field(default=80, ge=0, le=100, alias="ALERT_MIN_CRYPTO_SCORE")
    alert_min_stock_score: int = Field(default=80, ge=0, le=100, alias="ALERT_MIN_STOCK_SCORE")
    alert_min_options_score: int = Field(default=75, ge=0, le=100, alias="ALERT_MIN_OPTIONS_SCORE")
    alert_max_items_per_section: int = Field(default=10, ge=1, alias="ALERT_MAX_ITEMS_PER_SECTION")
    alert_include_risk_status: bool = Field(default=True, alias="ALERT_INCLUDE_RISK_STATUS")
    alert_include_safety_status: bool = Field(default=True, alias="ALERT_INCLUDE_SAFETY_STATUS")
    real_data_validation_enabled: bool = Field(default=False, alias="REAL_DATA_VALIDATION_ENABLED")
    real_data_validation_read_only: bool = Field(default=True, alias="REAL_DATA_VALIDATION_READ_ONLY")
    validation_symbols_crypto: list[str] = Field(default_factory=lambda: ["BTC/USD", "ETH/USD", "SOL/USD", "SUI/USD"], alias="VALIDATION_SYMBOLS_CRYPTO")
    validation_symbols_stock: list[str] = Field(default_factory=lambda: ["AAPL", "MSFT", "NVDA", "META", "TSLA"], alias="VALIDATION_SYMBOLS_STOCK")
    validation_timeframe_crypto: str = Field(default="1h", alias="VALIDATION_TIMEFRAME_CRYPTO")
    validation_timeframe_stock: str = Field(default="1d", alias="VALIDATION_TIMEFRAME_STOCK")
    validation_candle_limit: int = Field(default=250, ge=1, alias="VALIDATION_CANDLE_LIMIT")
    validation_require_safety_audit: bool = Field(default=True, alias="VALIDATION_REQUIRE_SAFETY_AUDIT")
    paper_observation_enabled: bool = Field(default=False, alias="PAPER_OBSERVATION_ENABLED")
    paper_observation_read_only: bool = Field(default=True, alias="PAPER_OBSERVATION_READ_ONLY")
    paper_observation_allow_paper_trades: bool = Field(default=False, alias="PAPER_OBSERVATION_ALLOW_PAPER_TRADES")
    paper_observation_symbols: list[str] = Field(default_factory=lambda: ["BTC/USD", "ETH/USD", "SOL/USD", "SUI/USD"], alias="PAPER_OBSERVATION_SYMBOLS")
    paper_observation_timeframe: str = Field(default="1h", alias="PAPER_OBSERVATION_TIMEFRAME")
    paper_observation_candle_limit: int = Field(default=250, ge=1, alias="PAPER_OBSERVATION_CANDLE_LIMIT")
    paper_observation_min_seconds_between_runs: int = Field(default=300, ge=0, alias="PAPER_OBSERVATION_MIN_SECONDS_BETWEEN_RUNS")
    paper_observation_max_symbols_per_run: int = Field(default=10, ge=1, alias="PAPER_OBSERVATION_MAX_SYMBOLS_PER_RUN")
    paper_observation_require_readiness: bool = Field(default=True, alias="PAPER_OBSERVATION_REQUIRE_READINESS")
    paper_observation_record_all_signals: bool = Field(default=True, alias="PAPER_OBSERVATION_RECORD_ALL_SIGNALS")
    paper_observation_record_rejected_risk: bool = Field(default=True, alias="PAPER_OBSERVATION_RECORD_REJECTED_RISK")
    calibration_enabled: bool = Field(default=True, alias="CALIBRATION_ENABLED")
    calibration_read_only: bool = Field(default=True, alias="CALIBRATION_READ_ONLY")
    calibration_min_observation_runs: int = Field(default=1, ge=1, alias="CALIBRATION_MIN_OBSERVATION_RUNS")
    calibration_warn_ema200_blocker_rate: float = Field(default=0.75, ge=0, le=1, alias="CALIBRATION_WARN_EMA200_BLOCKER_RATE")
    calibration_warn_low_score_rate: float = Field(default=0.75, ge=0, le=1, alias="CALIBRATION_WARN_LOW_SCORE_RATE")
    calibration_min_sample_size_for_changes: int = Field(default=20, ge=1, alias="CALIBRATION_MIN_SAMPLE_SIZE_FOR_CHANGES")
    calibration_allow_auto_apply: bool = Field(default=False, alias="CALIBRATION_ALLOW_AUTO_APPLY")
    observation_window_enabled: bool = Field(default=False, alias="OBSERVATION_WINDOW_ENABLED")
    observation_window_read_only: bool = Field(default=True, alias="OBSERVATION_WINDOW_READ_ONLY")
    observation_window_allow_paper_trades: bool = Field(default=False, alias="OBSERVATION_WINDOW_ALLOW_PAPER_TRADES")
    observation_window_default_runs: int = Field(default=6, ge=1, alias="OBSERVATION_WINDOW_DEFAULT_RUNS")
    observation_window_min_runs_for_summary: int = Field(default=3, ge=1, alias="OBSERVATION_WINDOW_MIN_RUNS_FOR_SUMMARY")
    observation_window_minutes_between_runs: int = Field(default=60, ge=0, alias="OBSERVATION_WINDOW_MINUTES_BETWEEN_RUNS")
    observation_window_max_runs_per_day: int = Field(default=12, ge=1, alias="OBSERVATION_WINDOW_MAX_RUNS_PER_DAY")
    observation_window_symbols: list[str] = Field(default_factory=lambda: ["BTC/USD", "ETH/USD", "SOL/USD", "SUI/USD"], alias="OBSERVATION_WINDOW_SYMBOLS")
    observation_window_timeframe: str = Field(default="1h", alias="OBSERVATION_WINDOW_TIMEFRAME")
    observation_window_candle_limit: int = Field(default=250, ge=1, alias="OBSERVATION_WINDOW_CANDLE_LIMIT")
    coinbase_api_key: str = Field(default="", alias="COINBASE_API_KEY")
    coinbase_api_secret: str = Field(default="", alias="COINBASE_API_SECRET")
    discord_webhook_url: str = Field(default="", alias="DISCORD_WEBHOOK_URL")

    @field_validator("allowed_symbols", "phase14_smoke_symbols", "validation_symbols_crypto", "paper_observation_symbols", "observation_window_symbols", mode="before")
    @classmethod
    def parse_allowed_symbols(cls, value: str | list[str]) -> list[str]:
        """Parse comma-delimited symbols from environment variables."""
        if isinstance(value, str):
            return [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
        return [symbol.upper() for symbol in value]

    @field_validator("stock_hunter_default_symbols", "validation_symbols_stock", mode="before")
    @classmethod
    def parse_stock_symbols(cls, value: str | list[str]) -> list[str]:
        """Parse comma-delimited stock symbols from environment variables."""
        if isinstance(value, str):
            return [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
        return [symbol.strip().upper() for symbol in value]

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
        if self.moomoo_trading_enabled or self.moomoo_paper_trading_enabled or self.moomoo_unlock_trade_context:
            raise ValueError("MooMoo trading, paper trading, and trade-context unlock are disabled in this phase")
        if not self.moomoo_read_only:
            raise ValueError("MOOMOO_READ_ONLY must remain true in this phase")
        if self.stock_hunter_allow_trading or not self.stock_hunter_read_only:
            raise ValueError("Stock Hunter must remain read-only with trading disabled in this phase")
        if self.stock_hunter_target_delta_min > self.stock_hunter_target_delta_max:
            raise ValueError("STOCK_HUNTER_TARGET_DELTA_MIN cannot exceed STOCK_HUNTER_TARGET_DELTA_MAX")
        if self.stock_hunter_ideal_rsi_min > self.stock_hunter_ideal_rsi_max:
            raise ValueError("STOCK_HUNTER_IDEAL_RSI_MIN cannot exceed STOCK_HUNTER_IDEAL_RSI_MAX")
        if self.stock_hunter_options_min_dte > self.stock_hunter_options_max_dte:
            raise ValueError("STOCK_HUNTER_OPTIONS_MIN_DTE cannot exceed STOCK_HUNTER_OPTIONS_MAX_DTE")
        if self.stock_hunter_options_target_dte_min > self.stock_hunter_options_target_dte_max:
            raise ValueError("STOCK_HUNTER_OPTIONS_TARGET_DTE_MIN cannot exceed STOCK_HUNTER_OPTIONS_TARGET_DTE_MAX")
        if not self.options_scanner_read_only or self.options_scanner_allow_execution:
            raise ValueError("Options scanner must remain read-only with execution disabled")
        if self.options_scanner_target_delta_min > self.options_scanner_target_delta_max:
            raise ValueError("OPTIONS_SCANNER_TARGET_DELTA_MIN cannot exceed OPTIONS_SCANNER_TARGET_DELTA_MAX")
        if self.options_scanner_min_dte > self.options_scanner_max_dte:
            raise ValueError("OPTIONS_SCANNER_MIN_DTE cannot exceed OPTIONS_SCANNER_MAX_DTE")
        if self.options_scanner_target_dte_min > self.options_scanner_target_dte_max:
            raise ValueError("OPTIONS_SCANNER_TARGET_DTE_MIN cannot exceed OPTIONS_SCANNER_TARGET_DTE_MAX")
        if not self.alerts_read_only:
            raise ValueError("ALERTS_READ_ONLY must remain true in this phase")
        if self.alert_channel_email:
            raise ValueError("Email alerts are disabled in this phase")
        if not self.real_data_validation_read_only:
            raise ValueError("REAL_DATA_VALIDATION_READ_ONLY must remain true in this phase")
        if not self.paper_observation_read_only:
            raise ValueError("PAPER_OBSERVATION_READ_ONLY must remain true in this phase")
        if not self.calibration_read_only or self.calibration_allow_auto_apply:
            raise ValueError("Calibration must remain read-only and auto-apply disabled")
        if not self.observation_window_read_only:
            raise ValueError("OBSERVATION_WINDOW_READ_ONLY must remain true in this phase")
        if self.observation_window_allow_paper_trades and not self.paper_observation_allow_paper_trades:
            raise ValueError("Observation window paper trades require paper observation paper trades to be enabled too")
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
