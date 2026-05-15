"""Risk validation and trade approval decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import Settings, get_settings
from app.risk.cooldown_manager import CooldownManager
from app.risk.kill_switch import KillSwitch
from app.risk.position_sizer import PositionSizer, PositionSizingError


@dataclass(frozen=True)
class RiskDecision:
    """Structured risk decision."""

    approved: bool
    symbol: str
    side: str
    requested_quantity: float | None
    approved_quantity: float | None
    max_quantity: float | None
    reasons: list[str]
    warnings: list[str]
    blockers: list[str]
    risk_amount: float | None
    estimated_notional: float | None
    source: str = "crypto_hunter_risk_v1"

    def to_dict(self) -> dict:
        """Return JSON-friendly output."""
        return asdict(self)


class RiskManager:
    """Evaluate proposed trades without executing them."""

    def __init__(
        self,
        settings: Settings | None = None,
        kill_switch: KillSwitch | None = None,
        cooldown_manager: CooldownManager | None = None,
        position_sizer: PositionSizer | None = None,
    ) -> None:
        """Initialize risk dependencies."""
        self.settings = settings or get_settings()
        self.kill_switch = kill_switch or KillSwitch(max_api_failures_before_kill=self.settings.max_api_failures_before_kill)
        self.cooldown_manager = cooldown_manager or CooldownManager(
            after_trade_minutes=self.settings.cooldown_after_trade_minutes,
            after_loss_minutes=self.settings.cooldown_after_loss_minutes,
        )
        self.position_sizer = position_sizer or PositionSizer()

    def can_open_position(self, open_positions: int, risk_fraction: float) -> bool:
        """Backward-compatible position count/risk check."""
        return not self.kill_switch.is_active() and open_positions < self.settings.max_open_positions and risk_fraction <= self.settings.max_risk_per_trade

    def evaluate_trade(
        self,
        symbol: str,
        side: str,
        signal_result: dict | Any,
        account_summary: dict,
        open_positions: list[dict] | dict,
        market_price: float,
        spread_bps: float | None = None,
        requested_quantity: float | None = None,
        manual_override: bool = False,
    ) -> RiskDecision:
        """Approve or reject a proposed trade without executing it."""
        normalized_symbol = self._normalize_symbol(symbol)
        side = side.lower().strip()
        reasons: list[str] = []
        warnings: list[str] = []
        blockers: list[str] = []

        positions = self._normalize_positions(open_positions)
        existing_position = positions.get(normalized_symbol)
        equity = float(account_summary.get("equity", 0) or 0)
        cash_balance = float(account_summary.get("cash_balance", 0) or 0)
        realized_pnl = float(account_summary.get("realized_pnl", 0) or 0)
        trades_today = int(account_summary.get("trades_today", account_summary.get("fills", 0)) or 0)
        consecutive_losses = int(account_summary.get("consecutive_losses", 0) or 0)
        score = int(self._signal_value(signal_result, "score", 0) or 0)
        category = str(self._signal_value(signal_result, "category", ""))
        signal_blockers = list(self._signal_value(signal_result, "blockers", []) or [])
        stop_loss = self._optional_float(self._signal_value(signal_result, "suggested_stop_loss", None))

        if self.kill_switch.is_active():
            blockers.append("kill switch is active")
        if self.cooldown_manager.is_symbol_on_cooldown(normalized_symbol):
            blockers.append("symbol cooldown is active")
        if score < self.settings.min_signal_score_to_trade:
            blockers.append("signal score below minimum")
        if category != "STRONG_BUY" and not manual_override:
            blockers.append("signal category is not STRONG_BUY")
        if signal_blockers:
            blockers.extend([f"signal blocker: {blocker}" for blocker in signal_blockers])
        if side not in {"buy", "sell"}:
            blockers.append("side must be buy or sell")
        if market_price <= 0:
            blockers.append("market price must be greater than zero")
        if spread_bps is not None and spread_bps > self.settings.max_spread_bps:
            blockers.append("spread exceeds maximum")
        if equity <= 0:
            blockers.append("account equity must be greater than zero")
        if realized_pnl < 0 and abs(realized_pnl) / max(equity, 1) >= self.settings.max_daily_loss:
            blockers.append("daily realized loss limit exceeded")
        if trades_today >= self.settings.max_trades_per_day:
            blockers.append("max trades per day exceeded")
        if consecutive_losses >= self.settings.max_consecutive_losses:
            blockers.append("consecutive loss limit exceeded")

        if side == "buy":
            if len(positions) >= self.settings.max_open_positions and existing_position is None:
                blockers.append("max open positions reached")
            if cash_balance <= 0:
                blockers.append("cash balance unavailable for buy")
        elif side == "sell":
            if existing_position is None:
                blockers.append("cannot sell without an existing position")
            elif requested_quantity is not None and requested_quantity > float(existing_position.get("quantity", 0)):
                blockers.append("cannot sell more than existing position")

        approved_quantity = None
        max_quantity = None
        risk_amount = None
        estimated_notional = None

        if not blockers and side == "buy":
            try:
                if stop_loss is None:
                    raise PositionSizingError("Suggested stop loss is required for buy risk sizing")
                risk_quantity = self.position_sizer.calculate_quantity_by_risk(equity, market_price, stop_loss, self.settings.max_risk_per_trade)
                risk_amount = equity * self.settings.max_risk_per_trade
                cash_capped = self.position_sizer.cap_quantity_by_cash(risk_quantity, cash_balance, market_price, self.settings.paper_fee_rate)
                allocation_capped = self._cap_quantity_with_existing_allocation(cash_capped, existing_position, equity, market_price)
                max_quantity = self.position_sizer.round_quantity(allocation_capped)
                if requested_quantity is not None and requested_quantity > max_quantity:
                    blockers.append("requested quantity exceeds maximum allowed by risk, cash, or allocation")
                    candidate = 0.0
                else:
                    candidate = requested_quantity if requested_quantity is not None else max_quantity
                approved_quantity = self.position_sizer.round_quantity(candidate)
                estimated_notional = approved_quantity * market_price
                if approved_quantity <= 0:
                    blockers.append("approved quantity is zero after risk caps")
                reasons.append("buy risk checks passed")
            except PositionSizingError as exc:
                blockers.append(str(exc))

        if not blockers and side == "sell":
            held_quantity = float(existing_position.get("quantity", 0)) if existing_position else 0.0
            candidate = requested_quantity if requested_quantity is not None else held_quantity
            approved_quantity = min(candidate, held_quantity)
            max_quantity = held_quantity
            estimated_notional = approved_quantity * market_price
            if approved_quantity <= 0:
                blockers.append("approved sell quantity is zero")
            else:
                reasons.append("sell risk checks passed for reducing existing position")

        approved = not blockers
        return RiskDecision(
            approved=approved,
            symbol=normalized_symbol,
            side=side,
            requested_quantity=requested_quantity,
            approved_quantity=approved_quantity if approved else None,
            max_quantity=max_quantity,
            reasons=reasons,
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
            risk_amount=risk_amount,
            estimated_notional=estimated_notional if approved else None,
        )

    def _cap_quantity_with_existing_allocation(self, quantity: float, existing_position: dict | None, equity: float, market_price: float) -> float:
        """Cap buy quantity by max allocation including existing market value."""
        max_value = equity * self.settings.max_position_allocation
        existing_value = float(existing_position.get("market_value", 0) or 0) if existing_position else 0.0
        remaining_value = max_value - existing_value
        if remaining_value <= 0:
            return 0.0
        return min(quantity, remaining_value / market_price)

    def _normalize_positions(self, open_positions: list[dict] | dict) -> dict[str, dict]:
        """Normalize open position structures into a symbol map."""
        if isinstance(open_positions, dict):
            values = open_positions.values()
        else:
            values = open_positions
        output = {}
        for position in values:
            if hasattr(position, "to_dict"):
                position = position.to_dict()
            symbol = self._normalize_symbol(str(position.get("symbol", "")))
            if symbol:
                output[symbol] = position
        return output

    def _signal_value(self, signal_result: dict | Any, key: str, default: Any) -> Any:
        """Read signal fields from dicts or dataclasses."""
        if isinstance(signal_result, dict):
            return signal_result.get(key, default)
        return getattr(signal_result, key, default)

    def _optional_float(self, value: Any) -> float | None:
        """Convert optional values to float."""
        if value is None:
            return None
        return float(value)

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize BTC-USD to BTC/USD."""
        return symbol.strip().upper().replace("-", "/")
