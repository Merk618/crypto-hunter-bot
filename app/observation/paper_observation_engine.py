"""Paper-only observation engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd

from app.config import Settings, get_settings
from app.data.market_data_service import MarketDataService
from app.execution.trade_executor import TradeExecutor
from app.observation.observation_models import ObservationResult, ObservationRun
from app.observation.observation_readiness import ObservationReadinessChecker
from app.observation.observation_report import build_observation_report
from app.observation.observation_scheduler import ObservationScheduler
from app.risk.risk_manager import RiskManager
from app.storage.trade_journal import TradeJournal
from app.strategies.crypto_hunter_strategy import CryptoHunterStrategy


class PaperObservationEngine:
    """Observe Kraken public data and optionally create paper-only trades."""

    def __init__(
        self,
        settings: Settings | None = None,
        market_data_service: MarketDataService | None = None,
        strategy: CryptoHunterStrategy | None = None,
        risk_manager: RiskManager | None = None,
        trade_executor: TradeExecutor | None = None,
        readiness_checker: ObservationReadinessChecker | None = None,
        scheduler: ObservationScheduler | None = None,
        journal: TradeJournal | None = None,
    ) -> None:
        """Initialize observation engine."""
        self.settings = settings or get_settings()
        self.market_data_service = market_data_service or MarketDataService(settings=self.settings)
        self.strategy = strategy or CryptoHunterStrategy()
        self.risk_manager = risk_manager or RiskManager(settings=self.settings)
        self.trade_executor = trade_executor or TradeExecutor(settings=self.settings)
        self.readiness_checker = readiness_checker or ObservationReadinessChecker()
        self.scheduler = scheduler or ObservationScheduler(self.settings.paper_observation_min_seconds_between_runs)
        self.journal = journal if journal is not None else (TradeJournal() if self.settings.enable_trade_journal else None)
        self.recent_runs: list[dict] = []

    def run_once(self, manual_run: bool = False, allow_paper_trades: bool = False) -> dict:
        """Run one observation pass without starting an infinite loop."""
        if not self.settings.paper_observation_enabled and not manual_run:
            return self._refused_run("paper observation disabled; pass manual_run=true")
        if not self.scheduler.can_run_now():
            return self._refused_run("minimum seconds between observation runs has not elapsed")
        readiness = {"ready": True, "blockers": [], "warnings": []}
        if self.settings.paper_observation_require_readiness:
            readiness = self.readiness_checker.check()
            if not readiness.get("ready") and not manual_run:
                return self._refused_run("observation readiness failed", readiness.get("blockers", []), readiness.get("warnings", []))

        run_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc).isoformat()
        self.scheduler.record_run_started()
        symbols = self.settings.paper_observation_symbols[: self.settings.paper_observation_max_symbols_per_run]
        results = [self.observe_symbol(symbol, allow_paper_trades=allow_paper_trades) for symbol in symbols]
        self.scheduler.record_run_completed()
        run = ObservationRun(
            run_id=run_id,
            started_at=started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            status="completed",
            symbols_requested=len(symbols),
            symbols_processed=len(results),
            signals_generated=sum(1 for result in results if result.signal is not None),
            risk_decisions_generated=sum(1 for result in results if result.risk_decision is not None),
            paper_trades_created=sum(1 for result in results if result.paper_trade_result is not None),
            warnings=list(readiness.get("warnings", [])),
            blockers=[blocker for result in results for blocker in result.blockers],
            results=[result.to_dict() for result in results],
        ).to_dict()
        self.recent_runs.insert(0, run)
        self.recent_runs = self.recent_runs[:500]
        return run

    def observe_symbol(self, symbol: str, allow_paper_trades: bool = False) -> ObservationResult:
        """Observe one symbol and return signal/risk/paper-only action."""
        normalized = symbol.strip().upper().replace("-", "/")
        try:
            candles = pd.DataFrame(self.market_data_service.get_symbol_candles(normalized, self.settings.paper_observation_timeframe, self.settings.paper_observation_candle_limit))
            signal = self.strategy.evaluate(candles, symbol=normalized, timeframe=self.settings.paper_observation_timeframe)
            market_price = float(signal.latest_price)
            account = self.trade_executor.get_paper_account_summary()
            positions = self.trade_executor.paper_broker.get_positions()
            risk = self.risk_manager.evaluate_trade(normalized, "buy", signal, account, positions, market_price)
            trade_result = None
            action = "observed"
            if allow_paper_trades and self.settings.paper_observation_allow_paper_trades and risk.approved and risk.approved_quantity:
                trade_result = self.trade_executor.execute_paper_market_order(normalized, "buy", risk.approved_quantity, market_price, f"paper observation signal score={signal.score}")
                action = "paper_buy"
            result = ObservationResult(
                symbol=normalized,
                timeframe=self.settings.paper_observation_timeframe,
                signal=signal,
                risk_decision=risk,
                paper_trade_result=trade_result,
                action_taken=action,
                reasons=list(signal.reasons) + list(risk.reasons),
                warnings=list(signal.warnings) + list(risk.warnings),
                blockers=list(signal.blockers) + list(risk.blockers),
            )
            self._journal(result)
            return result
        except Exception as exc:
            return ObservationResult(symbol=normalized, timeframe=self.settings.paper_observation_timeframe, action_taken="failed", blockers=[str(exc)])

    def get_status(self) -> dict:
        """Return observation status."""
        return {
            "enabled": self.settings.paper_observation_enabled,
            "read_only": self.settings.paper_observation_read_only,
            "paper_trades_allowed": self.settings.paper_observation_allow_paper_trades,
            "symbols": self.settings.paper_observation_symbols,
            "timeframe": self.settings.paper_observation_timeframe,
            "scheduler": self.scheduler.get_status(),
            "recent_runs": len(self.recent_runs),
            "source": "crypto_hunter_paper_observation_status_v1",
        }

    def get_recent_observations(self, limit: int = 50) -> dict:
        """Return recent in-memory observation runs."""
        return {"runs": self.recent_runs[:limit], "source": "crypto_hunter_recent_observations_v1"}

    def get_observation_report(self, limit: int = 100) -> dict:
        """Return observation report."""
        return build_observation_report(self.recent_runs, limit=limit).to_dict()

    def _refused_run(self, message: str, blockers: list[str] | None = None, warnings: list[str] | None = None) -> dict:
        """Return refused run."""
        return ObservationRun(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            status="refused",
            symbols_requested=0,
            symbols_processed=0,
            signals_generated=0,
            risk_decisions_generated=0,
            paper_trades_created=0,
            warnings=warnings or [],
            blockers=[message] + list(blockers or []),
        ).to_dict()

    def _journal(self, result: ObservationResult) -> None:
        """Record signal/risk observation artifacts without raising."""
        if not self.journal:
            return
        try:
            if result.signal is not None and self.settings.paper_observation_record_all_signals:
                self.journal.record_signal(result.signal)
            if result.risk_decision is not None and (result.risk_decision.approved or self.settings.paper_observation_record_rejected_risk):
                self.journal.record_risk_decision(result.risk_decision)
        except Exception:
            return
