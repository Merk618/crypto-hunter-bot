"""Read-only options contract ranking."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.stock_hunter.options_strategy_models import RankedOptionContract


class OptionsRankingEngine:
    """Rank normalized option contracts for research only."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize ranking thresholds."""
        self.settings = settings or get_settings()

    def rank_contracts(self, contracts: list[dict], underlying_score: float = 0, top_n: int | None = None) -> list[RankedOptionContract]:
        """Rank contracts by total research score."""
        ranked = [self.rank_contract(contract, underlying_score=underlying_score) for contract in contracts]
        ranked.sort(key=lambda contract: contract.total_score, reverse=True)
        for index, contract in enumerate(ranked, start=1):
            contract.rank = index
        if top_n is not None:
            return ranked[:top_n]
        return ranked

    def rank_contract(self, contract: dict, underlying_score: float = 0) -> RankedOptionContract:
        """Rank one normalized contract."""
        liquidity = self._num(contract.get("liquidity_score"))
        contract_score = self._num(contract.get("contract_score"))
        dte_quality = self._dte_quality(contract.get("dte"))
        spread_quality = self._spread_quality(contract.get("spread_pct"))
        delta_quality = self._delta_quality(contract.get("delta"))
        adjusted_contract_score = min(100.0, (contract_score * 0.8) + (delta_quality * 0.2))
        total = (liquidity * 0.30) + (adjusted_contract_score * 0.30) + (float(underlying_score) * 0.25) + (dte_quality * 0.10) + (spread_quality * 0.05)
        blockers = list(contract.get("blockers") or [])
        warnings = list(contract.get("warnings") or [])
        reasons = list(contract.get("reasons") or [])
        if contract.get("candidate_label") == "REJECTED":
            blockers.append("contract rejected by options filters")
        if float(underlying_score) < self.settings.options_scanner_min_underlying_score:
            warnings.append("underlying score below preferred floor")
        label = self._label(total, blockers, warnings)
        return RankedOptionContract(
            rank=None,
            symbol=str(contract.get("symbol", "")),
            underlying=str(contract.get("underlying", "")),
            expiration=contract.get("expiration"),
            dte=contract.get("dte"),
            strike=contract.get("strike"),
            option_type=str(contract.get("option_type", "")),
            bid=contract.get("bid"),
            ask=contract.get("ask"),
            mid=self._mid(contract.get("bid"), contract.get("ask")),
            last=contract.get("last"),
            volume=contract.get("volume"),
            open_interest=contract.get("open_interest"),
            implied_volatility=contract.get("implied_volatility"),
            delta=contract.get("delta"),
            gamma=contract.get("gamma"),
            theta=contract.get("theta"),
            vega=contract.get("vega"),
            spread_pct=contract.get("spread_pct"),
            liquidity_score=round(liquidity, 4),
            contract_score=round(adjusted_contract_score, 4),
            underlying_score=round(float(underlying_score), 4),
            total_score=round(total, 4),
            label=label,
            reasons=reasons,
            warnings=warnings,
            blockers=blockers,
        )

    def _label(self, total_score: float, blockers: list[str], warnings: list[str]) -> str:
        """Map score to a non-executable research label."""
        if blockers or total_score < 50:
            return "REJECTED"
        if total_score >= 75 and not any("below preferred floor" in warning for warning in warnings):
            return "RESEARCH_CANDIDATE"
        return "WATCHLIST_CANDIDATE"

    def _dte_quality(self, dte) -> float:
        """Score DTE fit from 0 to 100."""
        if dte is None:
            return 0.0
        dte = int(dte)
        if dte < self.settings.options_scanner_min_dte or dte > self.settings.options_scanner_max_dte:
            return 0.0
        if self.settings.options_scanner_target_dte_min <= dte <= self.settings.options_scanner_target_dte_max:
            return 100.0
        return 60.0

    def _spread_quality(self, spread_pct) -> float:
        """Score spread quality from 0 to 100."""
        spread = self._num(spread_pct)
        if spread <= 0:
            return 0.0
        if spread > self.settings.options_scanner_max_spread_pct:
            return 0.0
        return max(0.0, 100.0 * (1 - (spread / max(self.settings.options_scanner_max_spread_pct, 0.01))))

    def _delta_quality(self, delta) -> float:
        """Score delta quality from 0 to 100."""
        if delta is None:
            return 0.0
        absolute = abs(float(delta))
        if self.settings.options_scanner_target_delta_min <= absolute <= self.settings.options_scanner_target_delta_max:
            return 100.0
        distance = min(abs(absolute - self.settings.options_scanner_target_delta_min), abs(absolute - self.settings.options_scanner_target_delta_max))
        return max(0.0, 100.0 - (distance * 200))

    def _mid(self, bid, ask) -> float | None:
        """Return bid/ask midpoint."""
        if bid is None or ask is None:
            return None
        return round((float(bid) + float(ask)) / 2, 4)

    def _num(self, value) -> float:
        """Convert optional numeric value."""
        return 0.0 if value is None else float(value)
