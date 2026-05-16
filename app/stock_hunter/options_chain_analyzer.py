"""Read-only options chain analyzer."""

from __future__ import annotations

from datetime import date, datetime

from app.config import Settings, get_settings
from app.stock_hunter.stock_hunter_models import OptionContractSnapshot, OptionsChainAnalysis


class OptionsChainAnalyzer:
    """Score option contracts as research candidates only."""

    def __init__(self, settings: Settings | None = None, today: date | None = None) -> None:
        """Initialize analyzer thresholds."""
        self.settings = settings or get_settings()
        self.today = today

    def analyze(self, underlying: str, contracts: list[dict]) -> OptionsChainAnalysis:
        """Analyze contracts and return read-only ranked research candidates."""
        snapshots: list[OptionContractSnapshot] = []
        warnings: list[str] = []
        rejected = 0
        for raw in contracts:
            snapshot = self._snapshot(underlying, raw)
            if snapshot.candidate_label == "REJECTED":
                rejected += 1
            else:
                snapshots.append(snapshot)

        calls = sorted(
            [contract for contract in snapshots if contract.option_type == "call"],
            key=lambda contract: contract.contract_score,
            reverse=True,
        )[:5]
        puts = sorted(
            [contract for contract in snapshots if contract.option_type == "put"],
            key=lambda contract: contract.contract_score,
            reverse=True,
        )[:5]
        if not contracts:
            warnings.append("No option contracts supplied")

        return OptionsChainAnalysis(
            underlying=underlying.strip().upper(),
            contracts_analyzed=len(contracts),
            best_call_candidates=[contract.to_dict() for contract in calls],
            best_put_candidates=[contract.to_dict() for contract in puts],
            rejected_contracts_count=rejected,
            warnings=warnings,
        )

    def _snapshot(self, underlying: str, raw: dict) -> OptionContractSnapshot:
        """Convert raw contract data into a scored snapshot."""
        reasons: list[str] = []
        warnings: list[str] = []
        bid = self._optional_float(raw.get("bid"))
        ask = self._optional_float(raw.get("ask"))
        spread_pct = self._spread_pct(bid, ask)
        volume = self._optional_int(raw.get("volume"))
        open_interest = self._optional_int(raw.get("open_interest"))
        option_type = str(raw.get("option_type", "")).lower()
        delta = self._optional_float(raw.get("delta"))
        dte = self._dte(str(raw.get("expiration", "")))
        liquidity_score = self._liquidity_score(volume, open_interest, spread_pct)
        contract_score = self._contract_score(option_type, volume, open_interest, spread_pct, delta, dte, bid, ask, raw.get("implied_volatility"), reasons, warnings)
        label = self._candidate_label(contract_score, warnings)
        return OptionContractSnapshot(
            symbol=str(raw.get("symbol", "")),
            underlying=str(raw.get("underlying", underlying)).strip().upper(),
            expiration=str(raw.get("expiration", "")),
            strike=float(raw.get("strike", 0) or 0),
            option_type=option_type,
            bid=bid,
            ask=ask,
            last=self._optional_float(raw.get("last")),
            volume=volume,
            open_interest=open_interest,
            implied_volatility=self._optional_float(raw.get("implied_volatility")),
            delta=delta,
            gamma=self._optional_float(raw.get("gamma")),
            theta=self._optional_float(raw.get("theta")),
            vega=self._optional_float(raw.get("vega")),
            spread_pct=spread_pct,
            liquidity_score=liquidity_score,
            dte=dte,
            contract_score=contract_score,
            candidate_label=label,
            reasons=reasons,
            warnings=warnings,
        )

    def _contract_score(
        self,
        option_type: str,
        volume: int | None,
        open_interest: int | None,
        spread_pct: float | None,
        delta: float | None,
        dte: int | None,
        bid: float | None,
        ask: float | None,
        implied_volatility,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Return a 0-100 research score for a contract."""
        score = 0.0
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            warnings.append("invalid bid/ask")
            return 0.0
        reasons.append("bid/ask valid")

        if (volume or 0) >= self.settings.stock_hunter_min_option_volume:
            score += min(20, ((volume or 0) / max(self.settings.stock_hunter_min_option_volume, 1)) * 10)
            reasons.append("volume passes filter")
        else:
            warnings.append("volume below filter")

        if (open_interest or 0) >= self.settings.stock_hunter_min_option_open_interest:
            score += min(20, ((open_interest or 0) / max(self.settings.stock_hunter_min_option_open_interest, 1)) * 10)
            reasons.append("open interest passes filter")
        else:
            warnings.append("open interest below filter")

        if spread_pct is not None and spread_pct <= self.settings.stock_hunter_max_bid_ask_spread_pct:
            spread_ratio = spread_pct / max(self.settings.stock_hunter_max_bid_ask_spread_pct, 0.01)
            score += max(0, 20 * (1 - spread_ratio))
            reasons.append("spread passes filter")
        else:
            warnings.append("spread too wide or unavailable")

        abs_delta = abs(delta) if delta is not None else None
        if abs_delta is None:
            warnings.append("delta unavailable")
        elif self.settings.stock_hunter_target_delta_min <= abs_delta <= self.settings.stock_hunter_target_delta_max:
            score += 20
            reasons.append("delta in target range")
        elif option_type == "call":
            warnings.append("call delta outside target range")
        else:
            score += 8
            warnings.append("put delta outside target range")

        if dte is None:
            warnings.append("DTE unavailable")
        elif dte < self.settings.stock_hunter_options_min_dte:
            warnings.append("DTE below minimum")
        elif dte > self.settings.stock_hunter_options_max_dte:
            warnings.append("DTE above maximum")
        elif self.settings.stock_hunter_options_target_dte_min <= dte <= self.settings.stock_hunter_options_target_dte_max:
            score += 20
            reasons.append("DTE in preferred range")
        else:
            score += 10
            reasons.append("DTE in acceptable range")

        iv = self._optional_float(implied_volatility)
        if iv is None:
            warnings.append("implied volatility unavailable")
        elif iv > 1.0:
            warnings.append("implied volatility very high")
        return round(min(score, 100), 4)

    def _candidate_label(self, score: float, warnings: list[str]) -> str:
        """Map contract score and warnings to a research label."""
        hard_rejections = {
            "invalid bid/ask",
            "volume below filter",
            "open interest below filter",
            "spread too wide or unavailable",
            "delta unavailable",
            "DTE below minimum",
            "DTE above maximum",
            "call delta outside target range",
            "DTE unavailable",
        }
        if any(warning in hard_rejections for warning in warnings):
            return "REJECTED"
        if score >= 80:
            return "RESEARCH_CANDIDATE"
        if score >= 60:
            return "WATCHLIST_CANDIDATE"
        return "REJECTED"

    def _dte(self, expiration: str) -> int | None:
        """Calculate days to expiration."""
        if not expiration:
            return None
        try:
            expiration_date = datetime.fromisoformat(expiration[:10]).date()
        except ValueError:
            return None
        return (expiration_date - (self.today or date.today())).days

    def _spread_pct(self, bid: float | None, ask: float | None) -> float | None:
        """Calculate bid/ask spread percentage."""
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            return None
        mid = (bid + ask) / 2
        return ((ask - bid) / mid) * 100 if mid > 0 else None

    def _liquidity_score(self, volume: int | None, open_interest: int | None, spread_pct: float | None) -> float:
        """Calculate a normalized 0-100 liquidity score."""
        if spread_pct is None:
            return 0.0
        volume_score = min(((volume or 0) / max(self.settings.stock_hunter_min_option_volume, 1)) * 30, 30)
        oi_score = min(((open_interest or 0) / max(self.settings.stock_hunter_min_option_open_interest, 1)) * 30, 30)
        spread_score = max(0, 40 * (1 - (spread_pct / max(self.settings.stock_hunter_max_bid_ask_spread_pct, 0.01))))
        return round(min(volume_score + oi_score + spread_score, 100), 4)

    def _optional_float(self, value) -> float | None:
        """Convert optional float."""
        return None if value is None else float(value)

    def _optional_int(self, value) -> int | None:
        """Convert optional int."""
        return None if value is None else int(value)
