"""Trade journal persistence API."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select

from app.storage.database import get_db_session, init_db
from app.storage.models import (
    AccountSnapshotRecord,
    BotEventRecord,
    ErrorRecord,
    ObservationResultRecord,
    ObservationRunRecord,
    PaperFillRecord,
    PaperOrderRecord,
    PaperPositionRecord,
    RiskDecisionRecord,
    ScanResultRecord,
    SignalRecord,
)
from app.storage.serializers import dumps_json, loads_json, normalize_rejected_risk_payload, to_plain_data


class TradeJournal:
    """Write and read Crypto Hunter journal records."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize journal database access."""
        self.database_url = database_url

    def init(self) -> None:
        """Create all journal tables."""
        init_db(self.database_url)

    def record_bot_event(self, event_type: str, message: str, payload=None) -> dict:
        """Record a bot event."""
        record = BotEventRecord(event_type=event_type, message=message, payload_json=dumps_json(payload) if payload is not None else None)
        return self._add(record)

    def record_signal(self, signal_result) -> dict:
        """Record a signal result."""
        data = to_plain_data(signal_result)
        record = SignalRecord(
            symbol=data.get("symbol", ""),
            timeframe=data.get("timeframe", ""),
            score=int(data.get("score", 0)),
            raw_score=(data.get("component_scores") or {}).get("raw_score") or (data.get("metadata") or {}).get("raw_score_before_caps"),
            category=data.get("category", ""),
            risk_level=data.get("risk_level"),
            latest_price=data.get("latest_price"),
            suggested_entry=data.get("suggested_entry"),
            suggested_stop_loss=data.get("suggested_stop_loss"),
            suggested_take_profit=data.get("suggested_take_profit"),
            reasons_json=dumps_json(data.get("reasons", [])),
            warnings_json=dumps_json(data.get("warnings", [])),
            blockers_json=dumps_json(data.get("blockers", [])),
            component_scores_json=dumps_json(data.get("component_scores", {})),
            exit_watch=bool(data.get("exit_watch", False)),
            trim_zone=bool(data.get("trim_zone", False)),
            momentum_warning=data.get("momentum_warning"),
            source=data.get("source", "crypto_hunter_signal_v1"),
        )
        return self._add(record)

    def record_risk_decision(self, risk_decision) -> dict:
        """Record a risk decision."""
        data = normalize_rejected_risk_payload(to_plain_data(risk_decision))
        record = RiskDecisionRecord(
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            approved=bool(data.get("approved", False)),
            requested_quantity=data.get("requested_quantity"),
            approved_quantity=data.get("approved_quantity"),
            max_quantity=data.get("max_quantity"),
            risk_amount=data.get("risk_amount"),
            estimated_notional=data.get("estimated_notional"),
            reasons_json=dumps_json(data.get("reasons", [])),
            warnings_json=dumps_json(data.get("warnings", [])),
            blockers_json=dumps_json(data.get("blockers", [])),
            source=data.get("source", "crypto_hunter_risk_v1"),
        )
        return self._add(record)

    def record_paper_order(self, order) -> dict:
        """Record a paper order."""
        data = to_plain_data(order)
        record = PaperOrderRecord(
            order_id=data["order_id"],
            symbol=data["symbol"],
            side=data["side"],
            order_type=data["order_type"],
            quantity=data["quantity"],
            requested_price=data["requested_price"],
            simulated_fill_price=data.get("simulated_fill_price"),
            status=data["status"],
            reason=data.get("reason"),
            created_at=self._as_datetime(data["created_at"]),
            filled_at=self._as_datetime(data.get("filled_at")),
        )
        return self._add(record)

    def record_paper_fill(self, fill) -> dict:
        """Record a paper fill."""
        data = to_plain_data(fill)
        record = PaperFillRecord(
            fill_id=data["fill_id"],
            order_id=data["order_id"],
            symbol=data["symbol"],
            side=data["side"],
            quantity=data["quantity"],
            price=data["price"],
            fee=data["fee"],
            slippage=data["slippage"],
            timestamp=self._as_datetime(data["timestamp"]),
        )
        return self._add(record)

    def record_paper_position(self, position, status: str = "open") -> dict:
        """Record a paper position snapshot."""
        data = to_plain_data(position)
        record = PaperPositionRecord(
            symbol=data["symbol"],
            quantity=data["quantity"],
            average_entry_price=data["average_entry_price"],
            current_price=data["current_price"],
            market_value=data["market_value"],
            unrealized_pnl=data["unrealized_pnl"],
            realized_pnl=data["realized_pnl"],
            opened_at=self._as_datetime(data["opened_at"]),
            updated_at=self._as_datetime(data["updated_at"]),
            status=status,
        )
        return self._add(record)

    def record_account_snapshot(self, account_summary: dict) -> dict:
        """Record a paper account snapshot."""
        data = to_plain_data(account_summary)
        record = AccountSnapshotRecord(
            cash_balance=float(data.get("cash_balance", 0)),
            equity=float(data.get("equity", 0)),
            realized_pnl=float(data.get("realized_pnl", 0)),
            unrealized_pnl=float(data.get("unrealized_pnl", 0)),
            total_fees_paid=float(data.get("total_fees_paid", 0)),
            open_position_count=int(data.get("open_positions", data.get("open_position_count", 0)) or 0),
        )
        return self._add(record)

    def record_scan_result(self, scan_result) -> dict:
        """Record a scan result."""
        data = to_plain_data(scan_result)
        record = ScanResultRecord(
            symbol=data.get("symbol", ""),
            action_taken=data.get("action_taken", "none"),
            signal_json=dumps_json(data.get("signal")),
            risk_decision_json=dumps_json(data.get("risk_decision")),
            trade_result_json=dumps_json(data.get("trade_result")),
            reasons_json=dumps_json(data.get("reasons", [])),
            warnings_json=dumps_json(data.get("warnings", [])),
            blockers_json=dumps_json(data.get("blockers", [])),
            timestamp=self._as_datetime(data.get("timestamp")),
        )
        return self._add(record)

    def record_error(self, component: str, error_type: str, message: str, payload=None) -> dict:
        """Record an error."""
        record = ErrorRecord(component=component, error_type=error_type, message=message, payload_json=dumps_json(payload) if payload is not None else None)
        return self._add(record)

    def record_observation_run(self, run: dict) -> dict:
        """Record observation run metadata."""
        data = to_plain_data(run)
        record = ObservationRunRecord(
            run_id=data.get("run_id", ""),
            started_at=self._as_datetime(data.get("started_at")),
            completed_at=self._as_datetime(data.get("completed_at")),
            status=data.get("status", ""),
            symbols_requested=int(data.get("symbols_requested", 0) or 0),
            symbols_processed=int(data.get("symbols_processed", 0) or 0),
            signals_generated=int(data.get("signals_generated", 0) or 0),
            risk_decisions_generated=int(data.get("risk_decisions_generated", 0) or 0),
            paper_trades_created=int(data.get("paper_trades_created", 0) or 0),
            warnings_json=dumps_json(data.get("warnings", [])),
            blockers_json=dumps_json(data.get("blockers", [])),
            source=data.get("source", "crypto_hunter_observation_run_v1"),
        )
        return self._add(record)

    def record_observation_result(self, run_id: str, result: dict) -> dict:
        """Record one observation result."""
        data = to_plain_data(result)
        record = ObservationResultRecord(
            run_id=run_id,
            symbol=data.get("symbol", ""),
            timeframe=data.get("timeframe", ""),
            signal_json=dumps_json(data.get("signal")),
            risk_decision_json=dumps_json(data.get("risk_decision")),
            paper_trade_result_json=dumps_json(data.get("paper_trade_result")),
            action_taken=data.get("action_taken", "observed"),
            reasons_json=dumps_json(data.get("reasons", [])),
            warnings_json=dumps_json(data.get("warnings", [])),
            blockers_json=dumps_json(data.get("blockers", [])),
            observed_at=self._as_datetime(data.get("observed_at")),
            source=data.get("source", "crypto_hunter_observation_result_v1"),
        )
        return self._add(record)

    def record_observation_run_with_results(self, run: dict) -> dict:
        """Record an observation run and its nested results."""
        data = to_plain_data(run)
        run_record = self.record_observation_run(data)
        for result in data.get("results", []) or []:
            self.record_observation_result(data.get("run_id", ""), result)
        return run_record

    def get_recent_bot_events(self, limit: int = 50) -> list[dict]:
        """Return recent bot events."""
        return self._recent(BotEventRecord, limit)

    def get_recent_signals(self, limit: int = 50, symbol: str | None = None) -> list[dict]:
        """Return recent signals."""
        return self._recent(SignalRecord, limit, symbol)

    def get_recent_risk_decisions(self, limit: int = 50, symbol: str | None = None) -> list[dict]:
        """Return recent risk decisions."""
        return self._recent(RiskDecisionRecord, limit, symbol)

    def get_recent_orders(self, limit: int = 50, symbol: str | None = None) -> list[dict]:
        """Return recent paper orders."""
        return self._recent(PaperOrderRecord, limit, symbol)

    def get_recent_fills(self, limit: int = 50, symbol: str | None = None) -> list[dict]:
        """Return recent paper fills."""
        return self._recent(PaperFillRecord, limit, symbol)

    def get_recent_positions(self, symbol: str | None = None) -> list[dict]:
        """Return recent paper positions."""
        return self._recent(PaperPositionRecord, 500, symbol)

    def get_recent_account_snapshots(self, limit: int = 50) -> list[dict]:
        """Return recent account snapshots."""
        return self._recent(AccountSnapshotRecord, limit)

    def get_recent_scan_results(self, limit: int = 50, symbol: str | None = None) -> list[dict]:
        """Return recent scan results."""
        return self._recent(ScanResultRecord, limit, symbol)

    def get_recent_errors(self, limit: int = 50) -> list[dict]:
        """Return recent errors."""
        return self._recent(ErrorRecord, limit)

    def get_recent_observation_runs(self, limit: int = 50, completed_only: bool = False) -> list[dict]:
        """Return recent observation runs."""
        with get_db_session(self.database_url) as session:
            stmt = select(ObservationRunRecord).order_by(desc(ObservationRunRecord.id)).limit(limit)
            if completed_only:
                stmt = select(ObservationRunRecord).where(ObservationRunRecord.status == "completed").order_by(desc(ObservationRunRecord.id)).limit(limit)
            return [self._model_to_dict(row) for row in session.scalars(stmt).all()]

    def get_recent_observation_results(self, limit: int = 500, run_id: str | None = None, symbol: str | None = None) -> list[dict]:
        """Return recent observation results."""
        with get_db_session(self.database_url) as session:
            stmt = select(ObservationResultRecord).order_by(desc(ObservationResultRecord.id)).limit(limit)
            if run_id:
                stmt = select(ObservationResultRecord).where(ObservationResultRecord.run_id == run_id).order_by(desc(ObservationResultRecord.id)).limit(limit)
            if symbol:
                normalized = symbol.upper().replace("-", "/")
                if run_id:
                    stmt = select(ObservationResultRecord).where(ObservationResultRecord.run_id == run_id, ObservationResultRecord.symbol == normalized).order_by(desc(ObservationResultRecord.id)).limit(limit)
                else:
                    stmt = select(ObservationResultRecord).where(ObservationResultRecord.symbol == normalized).order_by(desc(ObservationResultRecord.id)).limit(limit)
            return [self._model_to_dict(row) for row in session.scalars(stmt).all()]

    def _add(self, record) -> dict:
        """Add a model and return dict output."""
        with get_db_session(self.database_url) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._model_to_dict(record)

    def _recent(self, model, limit: int, symbol: str | None = None) -> list[dict]:
        """Read recent model rows."""
        with get_db_session(self.database_url) as session:
            stmt = select(model).order_by(desc(model.id)).limit(limit)
            if symbol and hasattr(model, "symbol"):
                stmt = select(model).where(model.symbol == symbol.upper().replace("-", "/")).order_by(desc(model.id)).limit(limit)
            return [self._model_to_dict(row) for row in session.scalars(stmt).all()]

    def _model_to_dict(self, record) -> dict:
        """Convert SQLAlchemy record to dict and decode JSON fields."""
        output = {}
        for column in record.__table__.columns:
            value = getattr(record, column.name)
            if column.name.endswith("_json"):
                output[column.name] = value
                output[column.name.removesuffix("_json")] = loads_json(value)
            elif hasattr(value, "isoformat"):
                output[column.name] = value.isoformat()
            else:
                output[column.name] = value
        return output

    def _as_datetime(self, value) -> datetime | None:
        """Convert ISO strings or datetimes to datetime objects."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise TypeError(f"Unsupported datetime value: {value!r}")
