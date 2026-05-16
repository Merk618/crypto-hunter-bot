"""Strategy calibration report builder."""

from __future__ import annotations

from app.calibration.observation_analyzer import ObservationAnalyzer
from app.config import Settings, get_settings


class StrategyCalibrationReportBuilder:
    """Build read-only calibration reports from observation runs."""

    def __init__(self, settings: Settings | None = None, analyzer: ObservationAnalyzer | None = None) -> None:
        """Initialize report builder."""
        self.settings = settings or get_settings()
        self.analyzer = analyzer or ObservationAnalyzer(self.settings)

    def build(self, observation_runs: list[dict] | None) -> dict:
        """Return a JSON-friendly calibration report."""
        return self.analyzer.analyze_runs(observation_runs or []).to_dict()

    def build_for_symbol(self, symbol: str, observation_runs: list[dict] | None) -> dict:
        """Return a symbol-specific calibration summary."""
        normalized = symbol.strip().upper().replace("-", "/")
        results = []
        for run in observation_runs or []:
            for result in run.get("results", []) or []:
                result_symbol = str(result.get("symbol") or result.get("signal", {}).get("symbol") or "").upper().replace("-", "/")
                if result_symbol == normalized:
                    results.append(result)
        return self.analyzer.analyze_symbol(normalized, results).to_dict()

