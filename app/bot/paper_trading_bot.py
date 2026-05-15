"""Manual paper auto-trading bot loop."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from app.bot.bot_state import BotState
from app.bot.scan_result import ScanResult
from app.config import BotMode, Settings, get_settings
from app.data.market_data_service import MarketDataService
from app.execution.trade_executor import TradeExecutor
from app.risk.risk_manager import RiskManager
from app.storage.trade_journal import TradeJournal
from app.strategies.crypto_hunter_strategy import CryptoHunterStrategy


class PaperTradingBotError(RuntimeError):
    """Raised when paper bot lifecycle rules are violated."""


class PaperTradingBot:
    """Scan configured symbols and place paper buys only after signal and risk approval."""

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
        strategy: CryptoHunterStrategy | None = None,
        risk_manager: RiskManager | None = None,
        trade_executor: TradeExecutor | None = None,
        state: BotState | None = None,
        settings: Settings | None = None,
        journal: TradeJournal | None = None,
        now_fn=None,
    ) -> None:
        """Initialize the paper trading bot."""
        self.settings = settings or get_settings()
        self.market_data_service = market_data_service or MarketDataService(settings=self.settings)
        self.strategy = strategy or CryptoHunterStrategy()
        self.risk_manager = risk_manager or RiskManager(settings=self.settings)
        self.trade_executor = trade_executor or TradeExecutor(settings=self.settings)
        self.state = state or BotState()
        self.journal = journal if journal is not None else (TradeJournal() if self.settings.enable_trade_journal else None)
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def start(self, manual_start: bool = False) -> dict:
        """Start the paper bot without creating a blocking loop."""
        if self.settings.bot_mode != BotMode.PAPER:
            raise PaperTradingBotError("PaperTradingBot only starts in BOT_MODE=paper")
        if not self.settings.paper_auto_trading_enabled and not manual_start:
            raise PaperTradingBotError("PAPER_AUTO_TRADING_ENABLED=false; pass manual_start=true to start manually")
        self.state.start()
        self._journal_event("bot_started", "Paper bot started", {"manual_start": manual_start})
        return self.status()

    def stop(self) -> dict:
        """Stop the bot."""
        self.state.stop()
        self._journal_event("bot_stopped", "Paper bot stopped")
        return self.status()

    def pause(self) -> dict:
        """Pause the bot."""
        self.state.pause()
        self._journal_event("bot_paused", "Paper bot paused")
        return self.status()

    def resume(self) -> dict:
        """Resume the bot."""
        self.state.resume()
        self._journal_event("bot_resumed", "Paper bot resumed")
        return self.status()

    def status(self) -> dict:
        """Return bot status."""
        return self.state.to_dict()

    def scan_once(self) -> dict:
        """Run one watchlist scan."""
        if not self.state.is_running:
            raise PaperTradingBotError("Bot is stopped")
        if self.state.is_paused:
            raise PaperTradingBotError("Bot is paused")
        now = self._now_fn()
        if self.state.last_scan_at is not None:
            elapsed = (now - self.state.last_scan_at).total_seconds()
            if elapsed < self.settings.bot_min_seconds_between_scans:
                raise PaperTradingBotError("Minimum seconds between scans has not elapsed")

        self._journal_event("scan_started", "Paper scan started")
        results = self.run_watchlist_scan()
        self.state.last_scan_at = now
        self.state.scans_completed += 1
        trades_executed = sum(1 for result in results if result.action_taken == "paper_buy")
        self.state.paper_trades_executed += trades_executed
        self._journal_scan_results(results)
        self._journal_event("scan_completed", "Paper scan completed", {"symbols_scanned": len(results), "trades_executed": trades_executed})
        return {
            "scan_results": [result.to_dict() for result in results],
            "trades_executed": trades_executed,
            "symbols_scanned": len(results),
        }

    def run_watchlist_scan(self) -> list[ScanResult]:
        """Scan the configured allowed symbols once."""
        results = []
        traded_this_scan: set[str] = set()
        for symbol in self.settings.allowed_symbols[: self.settings.bot_max_symbols_per_scan]:
            normalized = self._normalize_symbol(symbol)
            if normalized in traded_this_scan:
                results.append(ScanResult(symbol=normalized, action_taken="none", blockers=["duplicate symbol trade prevented during scan"]))
                continue
            result = self.scan_symbol(normalized)
            if result.action_taken == "paper_buy":
                traded_this_scan.add(normalized)
            results.append(result)
        return results

    def scan_symbol(self, symbol: str) -> ScanResult:
        """Scan one symbol and maybe execute a paper buy."""
        normalized = self._normalize_symbol(symbol)
        try:
            candles = pd.DataFrame(
                self.market_data_service.get_symbol_candles(
                    normalized,
                    timeframe=self.settings.bot_scan_timeframe,
                    limit=self.settings.bot_scan_limit,
                )
            )
            signal = self.strategy.evaluate(candles, symbol=normalized, timeframe=self.settings.bot_scan_timeframe)
            market_price = float(signal.latest_price)
            account_summary = self.trade_executor.get_paper_account_summary()
            open_positions = self.trade_executor.paper_broker.get_positions()
            risk_decision = self.risk_manager.evaluate_trade(
                symbol=normalized,
                side="buy",
                signal_result=signal,
                account_summary=account_summary,
                open_positions=open_positions,
                market_price=market_price,
            )
            trade_result = self.maybe_execute_paper_trade(normalized, signal, risk_decision, market_price)
            action = "paper_buy" if trade_result and trade_result.get("accepted") else "none"
            return ScanResult(
                symbol=normalized,
                signal=signal,
                risk_decision=risk_decision,
                trade_result=trade_result,
                action_taken=action,
                reasons=list(signal.reasons) + list(risk_decision.reasons),
                warnings=list(signal.warnings) + list(risk_decision.warnings),
                blockers=list(signal.blockers) + list(risk_decision.blockers),
            )
        except Exception as exc:  # noqa: BLE001 - scan result should capture failures
            self.state.last_error = str(exc)
            if hasattr(self.risk_manager, "kill_switch"):
                self.risk_manager.kill_switch.record_api_failure()
            self._journal_error("paper_trading_bot", type(exc).__name__, str(exc), {"symbol": normalized})
            return ScanResult(symbol=normalized, action_taken="none", blockers=[str(exc)])

    def maybe_execute_paper_trade(self, symbol: str, signal_result, risk_decision, market_price: float) -> dict | None:
        """Execute a paper buy only when signal, risk, and config all allow it."""
        if not self.settings.paper_allow_autobuy:
            return None
        if signal_result.category != "STRONG_BUY":
            return None
        if signal_result.score < self.settings.min_signal_score_to_trade:
            return None
        if not risk_decision.approved:
            return None
        if risk_decision.approved_quantity is None or risk_decision.approved_quantity <= 0:
            return None
        reason = f"{self.settings.bot_default_order_reason}: {signal_result.category} score={signal_result.score}"
        return self.trade_executor.execute_paper_market_order(
            symbol=symbol,
            side="buy",
            quantity=risk_decision.approved_quantity,
            market_price=market_price,
            reason=reason,
        )

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize BTC-USD to BTC/USD."""
        return symbol.strip().upper().replace("-", "/")

    def _journal_scan_results(self, results: list[ScanResult]) -> None:
        """Record scan artifacts without raising."""
        if not self.journal:
            return
        for result in results:
            try:
                if result.signal is not None:
                    self.journal.record_signal(result.signal)
                if result.risk_decision is not None:
                    self.journal.record_risk_decision(result.risk_decision)
                self.journal.record_scan_result(result)
            except Exception as exc:  # noqa: BLE001
                self._journal_error("trade_journal", type(exc).__name__, str(exc), {"symbol": result.symbol})

    def _journal_event(self, event_type: str, message: str, payload=None) -> None:
        """Record bot event without raising."""
        if not self.journal:
            return
        try:
            self.journal.record_bot_event(event_type, message, payload)
        except Exception:
            return

    def _journal_error(self, component: str, error_type: str, message: str, payload=None) -> None:
        """Record bot error without raising."""
        if not self.journal:
            return
        try:
            self.journal.record_error(component, error_type, message, payload)
        except Exception:
            return
