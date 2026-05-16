"""Signal calibration diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.config import Settings, get_settings
from app.core.dependencies import get_market_data_service, get_strategy


@dataclass
class CalibrationSymbolReport:
    """Calibration summary for one symbol."""

    symbol: str
    timeframe: str
    latest_price: float | None
    signal_score: int | None
    category: str | None
    risk_level: str | None
    blockers: list[str]
    warnings: list[str]
    suggested_entry: float | None
    suggested_stop_loss: float | None
    suggested_take_profit: float | None
    calibration_status: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class CalibrationReport:
    """Build transparent diagnostics for current signal strictness."""

    STATUSES = {"TOO_STRICT", "NORMAL", "TOO_LOOSE", "BLOCKED", "DATA_UNAVAILABLE"}

    def __init__(self, settings: Settings | None = None, market_data_service=None, strategy=None) -> None:
        """Initialize calibration dependencies."""
        self.settings = settings or get_settings()
        self.market_data_service = market_data_service or get_market_data_service()
        self.strategy = strategy or get_strategy()

    def analyze_symbols(self, symbols: list[str] | None = None, timeframe: str | None = None, limit: int | None = None) -> dict:
        """Fetch data, generate signals, and return calibration reports."""
        symbols = symbols or self.settings.phase14_smoke_symbols
        timeframe = timeframe or self.settings.phase14_timeframe
        limit = limit or self.settings.phase14_candle_limit
        reports = []
        for symbol in symbols:
            try:
                candles = self.market_data_service.get_symbol_candles(symbol, timeframe=timeframe, limit=limit)
                signal = self.strategy.evaluate(pd.DataFrame(candles), symbol=symbol.upper().replace("-", "/"), timeframe=timeframe)
                reports.append(self.from_signal(signal).to_dict())
            except Exception as exc:  # noqa: BLE001 - diagnostics should report, not crash
                reports.append(
                    CalibrationSymbolReport(
                        symbol=symbol.upper().replace("-", "/"),
                        timeframe=timeframe,
                        latest_price=None,
                        signal_score=None,
                        category=None,
                        risk_level=None,
                        blockers=[str(exc)],
                        warnings=[],
                        suggested_entry=None,
                        suggested_stop_loss=None,
                        suggested_take_profit=None,
                        calibration_status="DATA_UNAVAILABLE",
                        notes=["Market data or signal generation unavailable"],
                    ).to_dict()
                )
        return self.summarize(reports)

    def from_signal(self, signal: Any) -> CalibrationSymbolReport:
        """Create a calibration row from one SignalResult-like object."""
        data = signal.to_dict() if hasattr(signal, "to_dict") else dict(signal)
        status, notes = self.classify_signal(data)
        return CalibrationSymbolReport(
            symbol=str(data.get("symbol", "")),
            timeframe=str(data.get("timeframe", self.settings.phase14_timeframe)),
            latest_price=data.get("latest_price"),
            signal_score=data.get("score"),
            category=data.get("category"),
            risk_level=data.get("risk_level"),
            blockers=list(data.get("blockers") or []),
            warnings=list(data.get("warnings") or []),
            suggested_entry=data.get("suggested_entry"),
            suggested_stop_loss=data.get("suggested_stop_loss"),
            suggested_take_profit=data.get("suggested_take_profit"),
            calibration_status=status,
            notes=notes,
        )

    def classify_signal(self, signal: dict) -> tuple[str, list[str]]:
        """Classify one signal without changing thresholds."""
        category = signal.get("category")
        blockers = list(signal.get("blockers") or [])
        risk_level = signal.get("risk_level")
        score = signal.get("score")
        notes: list[str] = []
        if category is None:
            return "DATA_UNAVAILABLE", ["No signal was available"]
        if blockers:
            if category in {"STRONG_BUY", "BUY_WATCH"}:
                notes.append("Bullish category is blocked by risk or trend constraints")
            else:
                notes.append("Signal is blocked by explicit blockers")
            return "BLOCKED", notes
        if category in {"STRONG_BUY", "BUY_WATCH"} and risk_level in {"HIGH", "EXTREME"}:
            return "TOO_LOOSE", ["Bullish category paired with elevated risk level"]
        if category in {"AVOID_SELL", "WEAK"} and score is not None and int(score) < 35:
            return "NORMAL", ["Weak signal appears consistent with low score"]
        return "NORMAL", ["Signal calibration appears reasonable"]

    def summarize(self, reports: list[dict]) -> dict:
        """Summarize calibration rows into a structured response."""
        if not reports:
            status = "DATA_UNAVAILABLE"
            notes = ["No signals available to calibrate"]
        else:
            statuses = [row.get("calibration_status") for row in reports]
            categories = [row.get("category") for row in reports]
            if all(status == "DATA_UNAVAILABLE" for status in statuses):
                status = "DATA_UNAVAILABLE"
                notes = ["All symbols failed due to unavailable data"]
            elif any(status == "TOO_LOOSE" for status in statuses):
                status = "TOO_LOOSE"
                notes = ["At least one bullish signal appears too permissive for its risk context"]
            elif all(status in {"BLOCKED", "DATA_UNAVAILABLE"} for status in statuses):
                status = "BLOCKED"
                notes = ["Signals are blocked or unavailable across the checked set"]
            elif not any(category in {"BUY_WATCH", "STRONG_BUY"} for category in categories if category):
                status = "NORMAL"
                notes = ["No bullish setup appeared in the checked market snapshot"]
            else:
                status = "NORMAL"
                notes = ["Calibration appears balanced for the checked symbols"]
        return {
            "passed": status not in {"TOO_LOOSE", "TOO_STRICT", "DATA_UNAVAILABLE"},
            "overall_status": status,
            "notes": notes,
            "reports": reports,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "crypto_hunter_phase14_calibration_report",
        }

    def synthetic_strictness_check(self, signals: list[dict]) -> str:
        """Classify synthetic bullish coverage for tests and manual diagnostics."""
        if not signals:
            return "DATA_UNAVAILABLE"
        bullish = [signal for signal in signals if signal.get("category") in {"BUY_WATCH", "STRONG_BUY"}]
        if not bullish:
            return "TOO_STRICT"
        if any(signal.get("category") == "STRONG_BUY" and signal.get("risk_level") in {"HIGH", "EXTREME"} for signal in signals):
            return "TOO_LOOSE"
        return "NORMAL"
