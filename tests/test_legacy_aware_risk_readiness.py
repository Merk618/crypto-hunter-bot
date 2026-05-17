"""Legacy-aware risk readiness tests."""

from app.risk.risk_readiness import RiskReadiness
from app.risk.risk_record_hygiene import RiskRecordHygiene
from app.observation.paper_trade_readiness import PaperTradeReadinessService


def record(**kwargs):
    """Build synthetic risk record."""
    data = {
        "id": 1,
        "symbol": "BTC/USD",
        "side": "buy",
        "approved": False,
        "approved_quantity": None,
        "max_quantity": None,
        "risk_amount": None,
        "estimated_notional": None,
        "blockers": ["signal score below minimum"],
        "reasons": [],
        "warnings": [],
        "source": "crypto_hunter_risk_v1",
    }
    data.update(kwargs)
    return data


class Hygiene(RiskRecordHygiene):
    """Risk hygiene using synthetic records."""

    def __init__(self, records):
        super().__init__()
        self.records = records

    def summary(self, records=None, limit=500):
        return super().summary(records=self.records, limit=limit)

    def validate_recent_records_only(self, limit=None):
        return super().validate_recent_records_only_from_records(self.records, limit)

    def legacy_aware_readiness(self, records=None, limit=None):
        return super().legacy_aware_readiness(records=self.records, limit=limit)


def test_legacy_inconsistent_records_warn_when_warn_only() -> None:
    """Legacy inconsistencies warn by default."""
    report = RiskRecordHygiene().validate_recent_records_only_from_records([record(approved_quantity=1.0, risk_amount=10.0)])

    assert report["passed"] is True
    assert report["legacy_warn_only"] is True
    assert report["legacy_inconsistency_count"] > 0
    assert report["blocking_inconsistency_count"] == 0


def test_current_inconsistent_records_still_block() -> None:
    """Current inconsistencies still block readiness."""
    report = RiskRecordHygiene().validate_recent_records_only_from_records([record(source="crypto_hunter_risk_v2", approved_quantity=1.0)])

    assert report["passed"] is False
    assert report["current_inconsistency_count"] > 0
    assert report["blocking_inconsistency_count"] > 0


def test_legacy_aware_readiness_passes_current_clean_with_legacy_present() -> None:
    """Risk readiness can pass current cleanliness while warning on legacy."""
    report = RiskRecordHygiene().legacy_aware_readiness(records=[record(approved_quantity=1.0)])

    assert report["passed"] is True
    assert report["current_clean"] is True
    assert report["legacy_present"] is True
    assert report["warnings"]


def test_risk_readiness_blocks_current_inconsistency() -> None:
    """RiskReadiness blocks on current inconsistent records."""
    readiness = RiskReadiness(Hygiene([record(source="crypto_hunter_risk_v2", approved_quantity=1.0)]))
    report = readiness.check()

    assert report["ready"] is False
    assert report["legacy_aware_readiness"]["current_clean"] is False


class Obj:
    """to_dict fake."""

    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data


class Safety:
    """Safe audit fake."""

    def run(self):
        return Obj({"passed": True, "live_trading_locked": True, "no_add_order_detected": True, "blockers": []})


def observation_runs(category="NEUTRAL", risk=False):
    """Build observation runs with enough results."""
    return [
        {
            "run_id": f"run-{idx}",
            "status": "completed",
            "results": [
                {
                    "symbol": "SUI/USD",
                    "signal": {"symbol": "SUI/USD", "score": 61, "category": category, "blockers": ["close at or below EMA 200"], "reasons": ["MACD positive momentum"]},
                    "risk_decision": {"approved": risk},
                    "blockers": ["close at or below EMA 200"],
                    "reasons": ["MACD positive momentum"],
                }
                for _ in range(4)
            ],
        }
        for idx in range(5)
    ]


def test_paper_readiness_remains_not_ready_without_strong_buy() -> None:
    """Paper readiness remains blocked/not ready without STRONG_BUY observations."""
    service = PaperTradeReadinessService(safety_audit=Safety(), risk_hygiene=Hygiene([record(approved_quantity=1.0)]))
    report = service.check(runs=observation_runs())

    assert report["paper_trade_observation_allowed_now"] is False
    assert report["strong_buy_count"] == 0
    assert any(check["name"] == "strong_buy_signals" and not check["passed"] for check in report["checks"])
    assert any("Legacy risk records" in warning for warning in report["warnings"])


def test_paper_readiness_remains_not_ready_without_risk_approvals() -> None:
    """Paper readiness remains blocked/not ready without risk-approved observations."""
    service = PaperTradeReadinessService(safety_audit=Safety(), risk_hygiene=Hygiene([record()]))
    report = service.check(runs=observation_runs(category="STRONG_BUY", risk=False))

    assert report["paper_trade_observation_allowed_now"] is False
    assert report["risk_approved_count"] == 0
    assert any(check["name"] == "risk_approvals" and not check["passed"] for check in report["checks"])
