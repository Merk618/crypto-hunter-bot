"""Order intent validation."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.execution.order_intent import OrderIntent, OrderValidationResult


class OrderValidator:
    """Validate order intents for dry-run execution only."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize validator."""
        self.settings = settings or get_settings()

    def validate_order_intent(self, intent: OrderIntent, risk_decision, account_summary: dict | None = None, ticker: dict | None = None, asset_pair_constraints: dict | None = None) -> OrderValidationResult:
        """Validate an order intent without placing an order."""
        blockers: list[str] = []
        warnings: list[str] = []
        checks: dict = {}
        normalized = intent.symbol.upper().replace("-", "/")

        if not self.settings.dry_run_execution_enabled:
            blockers.append("dry-run execution is disabled")
        if not self.settings.live_trading_gate_enabled:
            warnings.append("live trading gate is locked; dry-run validation only")
        if intent.side not in {"buy", "sell"}:
            blockers.append("side must be buy or sell")
        if intent.order_type != "market":
            blockers.append("only market order intents are supported")
        if intent.quantity <= 0:
            blockers.append("quantity must be greater than zero")
        if intent.estimated_price <= 0:
            blockers.append("estimated price must be greater than zero")
        if intent.estimated_notional < self.settings.min_order_notional_usd:
            blockers.append("estimated notional below minimum")
        if intent.estimated_notional > self.settings.max_order_notional_usd:
            blockers.append("estimated notional above maximum")
        if self.settings.require_risk_approval_for_orders and not self._risk_approved(intent, risk_decision):
            blockers.append("risk approval is required")
        if intent.signal_score < self.settings.min_signal_score_to_trade:
            blockers.append("signal score below trade threshold")
        if intent.side == "buy" and intent.signal_category != "STRONG_BUY":
            blockers.append("buy intent requires STRONG_BUY signal category")

        if ticker:
            self._validate_ticker(ticker, blockers, warnings, checks)
        elif self.settings.require_market_data_freshness:
            blockers.append("fresh ticker data is required")

        if self.settings.require_account_balance_check and account_summary is not None:
            self._validate_balance(intent, account_summary, blockers, checks)
        elif self.settings.require_account_balance_check:
            blockers.append("account balance check is required")

        if asset_pair_constraints:
            self._validate_constraints(intent, asset_pair_constraints, blockers, warnings, checks)

        approved = not blockers
        return OrderValidationResult(
            approved=approved,
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            side=intent.side,
            normalized_symbol=normalized,
            approved_quantity=intent.quantity if approved else None,
            estimated_price=intent.estimated_price,
            estimated_notional=intent.estimated_notional,
            blockers=list(dict.fromkeys(blockers)),
            warnings=list(dict.fromkeys(warnings)),
            checks=checks,
        )

    def _risk_approved(self, intent: OrderIntent, risk_decision) -> bool:
        """Return risk approval from intent or decision."""
        if risk_decision is None:
            return intent.risk_approved
        if isinstance(risk_decision, dict):
            return bool(risk_decision.get("approved", False))
        return bool(getattr(risk_decision, "approved", False))

    def _validate_ticker(self, ticker: dict, blockers: list[str], warnings: list[str], checks: dict) -> None:
        """Validate spread and freshness."""
        bid = float(ticker.get("bid") or 0)
        ask = float(ticker.get("ask") or 0)
        if self.settings.require_spread_check and bid > 0 and ask > 0:
            mid = (bid + ask) / 2
            spread_bps = ((ask - bid) / mid) * 10000 if mid > 0 else 0
            checks["spread_bps"] = spread_bps
            if spread_bps > self.settings.max_allowed_slippage_bps:
                blockers.append("spread exceeds allowed slippage")
        elif self.settings.require_spread_check:
            blockers.append("valid bid/ask spread data is required")

        if self.settings.require_market_data_freshness:
            ts = ticker.get("timestamp")
            if not ts:
                blockers.append("ticker timestamp is required")
                return
            timestamp = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            checks["market_data_age_seconds"] = age
            if age > self.settings.market_data_stale_seconds:
                blockers.append("ticker data is stale")

    def _validate_balance(self, intent: OrderIntent, account_summary: dict, blockers: list[str], checks: dict) -> None:
        """Validate account balance availability."""
        if intent.side == "buy":
            cash = float(account_summary.get("cash_balance", account_summary.get("available_usd", 0)) or 0)
            checks["available_cash"] = cash
            if cash < intent.estimated_notional:
                blockers.append("insufficient cash balance")
        if intent.side == "sell":
            positions = account_summary.get("positions", {})
            held = 0.0
            if isinstance(positions, dict):
                held = float((positions.get(intent.symbol) or positions.get(intent.symbol.upper().replace("-", "/")) or {}).get("quantity", 0) or 0)
            checks["held_quantity"] = held
            if held < intent.quantity:
                blockers.append("sell quantity exceeds available position")

    def _validate_constraints(self, intent: OrderIntent, constraints: dict, blockers: list[str], warnings: list[str], checks: dict) -> None:
        """Validate precision and minimum order size."""
        min_qty = constraints.get("min_quantity")
        min_notional = constraints.get("min_notional")
        quantity_decimals = constraints.get("quantity_decimals")
        if min_qty is not None and intent.quantity < float(min_qty):
            blockers.append("quantity below exchange minimum")
        if min_notional is not None and intent.estimated_notional < float(min_notional):
            blockers.append("notional below exchange minimum")
        if quantity_decimals is not None:
            rounded = round(intent.quantity, int(quantity_decimals))
            checks["rounded_quantity"] = rounded
            if abs(rounded - intent.quantity) > 1e-12:
                warnings.append("quantity precision would be rounded")
