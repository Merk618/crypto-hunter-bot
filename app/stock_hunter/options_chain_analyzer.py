"""Read-only options chain analyzer."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.stock_hunter.stock_hunter_models import OptionContractSnapshot, OptionsChainAnalysis


class OptionsChainAnalyzer:
    """Filter option contracts for research candidates only."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize analyzer thresholds."""
        self.settings = settings or get_settings()

    def analyze(self, underlying: str, contracts: list[dict]) -> OptionsChainAnalysis:
        """Analyze contracts and return research candidates."""
        candidates: list[OptionContractSnapshot] = []
        warnings: list[str] = []
        rejected = 0
        for raw in contracts:
            snapshot = self._snapshot(underlying, raw)
            if self._passes(snapshot):
                candidates.append(snapshot)
            else:
                rejected += 1

        calls = sorted([c for c in candidates if c.option_type == "call"], key=lambda c: c.liquidity_score, reverse=True)[:5]
        puts = sorted([c for c in candidates if c.option_type == "put"], key=lambda c: c.liquidity_score, reverse=True)[:5]
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

    def _passes(self, contract: OptionContractSnapshot) -> bool:
        """Return whether a contract passes research filters."""
        if contract.bid is None or contract.ask is None or contract.bid <= 0 or contract.ask <= 0:
            return False
        if (contract.volume or 0) < self.settings.stock_hunter_min_option_volume:
            return False
        if (contract.open_interest or 0) < self.settings.stock_hunter_min_option_open_interest:
            return False
        if contract.spread_pct is None or contract.spread_pct > self.settings.stock_hunter_max_bid_ask_spread_pct:
            return False
        if contract.option_type == "call":
            if contract.delta is None or not (self.settings.stock_hunter_target_delta_min <= contract.delta <= self.settings.stock_hunter_target_delta_max):
                return False
        return True

    def _snapshot(self, underlying: str, raw: dict) -> OptionContractSnapshot:
        """Convert raw contract data into a snapshot."""
        bid = self._optional_float(raw.get("bid"))
        ask = self._optional_float(raw.get("ask"))
        spread_pct = self._spread_pct(bid, ask)
        volume = self._optional_int(raw.get("volume"))
        open_interest = self._optional_int(raw.get("open_interest"))
        liquidity_score = self._liquidity_score(volume, open_interest, spread_pct)
        return OptionContractSnapshot(
            symbol=str(raw.get("symbol", "")),
            underlying=str(raw.get("underlying", underlying)).strip().upper(),
            expiration=str(raw.get("expiration", "")),
            strike=float(raw.get("strike", 0) or 0),
            option_type=str(raw.get("option_type", "")).lower(),
            bid=bid,
            ask=ask,
            last=self._optional_float(raw.get("last")),
            volume=volume,
            open_interest=open_interest,
            implied_volatility=self._optional_float(raw.get("implied_volatility")),
            delta=self._optional_float(raw.get("delta")),
            gamma=self._optional_float(raw.get("gamma")),
            theta=self._optional_float(raw.get("theta")),
            vega=self._optional_float(raw.get("vega")),
            spread_pct=spread_pct,
            liquidity_score=liquidity_score,
        )

    def _spread_pct(self, bid: float | None, ask: float | None) -> float | None:
        """Calculate bid/ask spread percentage."""
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            return None
        mid = (bid + ask) / 2
        return ((ask - bid) / mid) * 100 if mid > 0 else None

    def _liquidity_score(self, volume: int | None, open_interest: int | None, spread_pct: float | None) -> float:
        """Calculate a simple liquidity score."""
        if spread_pct is None:
            return 0.0
        volume_score = min((volume or 0) / max(self.settings.stock_hunter_min_option_volume, 1), 5)
        oi_score = min((open_interest or 0) / max(self.settings.stock_hunter_min_option_open_interest, 1), 5)
        spread_score = max(0, 5 - spread_pct)
        return round(volume_score + oi_score + spread_score, 4)

    def _optional_float(self, value) -> float | None:
        """Convert optional float."""
        return None if value is None else float(value)

    def _optional_int(self, value) -> int | None:
        """Convert optional int."""
        return None if value is None else int(value)
