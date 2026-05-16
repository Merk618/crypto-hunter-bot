"""Read-only real-data validation runner."""

from __future__ import annotations

import pandas as pd

from app.alerts.alert_service import AlertService
from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.core.safety_audit import SafetyAudit
from app.data.market_data_service import MarketDataService
from app.operator.operator_service import OperatorService
from app.stock_hunter.stock_hunter_service import StockHunterService
from app.strategies.crypto_hunter_strategy import CryptoHunterStrategy
from app.validation.real_data_validation_models import ValidationCheck
from app.validation.validation_report import build_validation_report


class RealDataValidator:
    """Run safe real-data validation checks."""

    def __init__(
        self,
        settings: Settings | None = None,
        safety_audit: SafetyAudit | None = None,
        market_data_service: MarketDataService | None = None,
        crypto_strategy: CryptoHunterStrategy | None = None,
        moomoo_client: MooMooReadOnlyClient | None = None,
        stock_service: StockHunterService | None = None,
        alert_service: AlertService | None = None,
        operator_service: OperatorService | None = None,
    ) -> None:
        """Initialize validation dependencies."""
        self.settings = settings or get_settings()
        self.safety_audit = safety_audit or SafetyAudit(settings=self.settings)
        self.market_data_service = market_data_service or MarketDataService(settings=self.settings)
        self.crypto_strategy = crypto_strategy or CryptoHunterStrategy()
        self.moomoo_client = moomoo_client or MooMooReadOnlyClient(settings=self.settings)
        self.stock_service = stock_service or StockHunterService(settings=self.settings)
        self.alert_service = alert_service or AlertService(settings=self.settings)
        self.operator_service = operator_service or OperatorService(settings=self.settings)

    def run_all_checks(self) -> dict:
        """Run all read-only validation checks."""
        checks = [
            self.validate_safety_audit(),
            self.validate_kraken_public_data(),
            self.validate_crypto_signals(),
            self.validate_moomoo_health(),
            self.validate_stock_hunter(),
            self.validate_options_scanner(),
            self.validate_alerts_reporting(),
            self.validate_operator_layer(),
        ]
        return build_validation_report(checks).to_dict()

    def validate_safety_audit(self) -> ValidationCheck:
        """Validate safety audit."""
        try:
            report = self.safety_audit.run().to_dict()
            return ValidationCheck("safety_audit", bool(report.get("passed")), "passed" if report.get("passed") else "failed", "Safety audit completed", warnings=report.get("warnings", []), blockers=report.get("blockers", []), metadata={"live_trading_locked": report.get("live_trading_locked")})
        except Exception as exc:
            return self._failed("safety_audit", "Safety audit unavailable", exc, "Run /system/safety-audit and review blockers")

    def validate_kraken_public_data(self) -> ValidationCheck:
        """Validate Kraken public ticker and candles."""
        try:
            symbol = self.settings.validation_symbols_crypto[0]
            ticker = self.market_data_service.get_symbol_ticker(symbol)
            candles = self.market_data_service.get_symbol_candles(symbol, self.settings.validation_timeframe_crypto, min(self.settings.validation_candle_limit, 250))
            passed = bool(ticker and candles)
            return ValidationCheck("kraken_public_data", passed, "passed" if passed else "failed", f"Validated Kraken public data for {symbol}", metadata={"symbol": symbol, "candles": len(candles)})
        except Exception as exc:
            return self._failed("kraken_public_data", "Kraken public data unavailable", exc, "Check internet access, Kraken status, and /market/ticker/BTC-USD")

    def validate_crypto_signals(self) -> ValidationCheck:
        """Validate crypto signal generation from public candles."""
        try:
            symbol = self.settings.validation_symbols_crypto[0]
            candles = self.market_data_service.get_symbol_candles(symbol, self.settings.validation_timeframe_crypto, self.settings.validation_candle_limit)
            df = pd.DataFrame(candles)
            signal = self.crypto_strategy.evaluate(df, symbol=symbol, timeframe=self.settings.validation_timeframe_crypto)
            return ValidationCheck("crypto_signals", True, "passed", f"Generated crypto signal for {symbol}", metadata={"score": signal.score, "category": signal.category})
        except Exception as exc:
            return self._failed("crypto_signals", "Crypto signal validation unavailable", exc, "Confirm Kraken candles return enough data for indicators")

    def validate_moomoo_health(self) -> ValidationCheck:
        """Validate MooMoo read-only health."""
        try:
            health = self.moomoo_client.get_health().to_dict()
            if not health.get("enabled"):
                return ValidationCheck("moomoo_readonly", False, "disabled", "MooMoo is disabled; enable MOOMOO_ENABLED only after OpenD is installed", warnings=["MooMoo disabled"], metadata=health)
            if not health.get("connected"):
                return ValidationCheck("moomoo_readonly", False, "disconnected", "MooMoo OpenD is not connected", warnings=["OpenD disconnected"], metadata=health)
            passed = bool(health.get("read_only") and not health.get("trading_enabled") and not health.get("unlock_trade_context"))
            return ValidationCheck("moomoo_readonly", passed, "passed" if passed else "failed", "MooMoo read-only health checked", metadata=health)
        except Exception as exc:
            return self._failed("moomoo_readonly", "MooMoo health unavailable", exc, "Check moomoo-api package and OpenD")

    def validate_stock_hunter(self) -> ValidationCheck:
        """Validate Stock Hunter endpoint/service behavior."""
        try:
            result = self.stock_service.top_candidates(limit=3)
            warnings = [] if result.get("results") else ["No stock candidates available; MooMoo may be disabled or disconnected"]
            return ValidationCheck("stock_hunter", True, "passed", "Stock Hunter returned a clean response", warnings=warnings, metadata={"candidate_count": len(result.get("results", []))})
        except Exception as exc:
            return self._failed("stock_hunter", "Stock Hunter unavailable", exc, "Check /stock-hunter/status and MooMoo health")

    def validate_options_scanner(self) -> ValidationCheck:
        """Validate Options Scanner behavior."""
        try:
            result = self.stock_service.top_options(limit=3)
            warnings = [] if result.get("top_candidates") else ["No option candidates available; MooMoo options may be unavailable"]
            return ValidationCheck("options_scanner", True, "passed", "Options Scanner returned a clean response", warnings=warnings, metadata={"candidate_count": len(result.get("top_candidates", []))})
        except Exception as exc:
            return self._failed("options_scanner", "Options Scanner unavailable", exc, "Check /options-scanner/status and MooMoo option permissions")

    def validate_alerts_reporting(self) -> ValidationCheck:
        """Validate alerts/reporting previews."""
        try:
            preview = self.alert_service.preview_alert_report()
            passed = "report" in preview
            return ValidationCheck("alerts_reporting", passed, "passed" if passed else "failed", "Alert preview and reports are available", metadata={"source": preview.get("source")})
        except Exception as exc:
            return self._failed("alerts_reporting", "Alerts/reporting unavailable", exc, "Check /alerts/preview and /reports/unified-summary")

    def validate_operator_layer(self) -> ValidationCheck:
        """Validate operator layer."""
        try:
            status = self.operator_service.get_operator_status()
            return ValidationCheck("operator_layer", bool(status.get("live_trading_locked")), "passed", "Operator status is available", warnings=status.get("warnings", []), blockers=status.get("blockers", []), metadata={"backend_healthy": status.get("backend_healthy")})
        except Exception as exc:
            return self._failed("operator_layer", "Operator layer unavailable", exc, "Check /operator/status")

    def _failed(self, name: str, message: str, exc: Exception, action: str) -> ValidationCheck:
        """Return failed check with actionable guidance."""
        return ValidationCheck(name, False, "failed", message, warnings=[action], blockers=[str(exc)], metadata={"exception_type": type(exc).__name__})
