"""Phase 23 reporting hygiene tests."""

from app.reporting.unified_report_service import UnifiedReportService


class Dashboard:
    """Dashboard fake with polluted signals."""

    def get_signal_performance(self, limit=100):
        return Obj({
            "recent_signals": [
                {"symbol": "BTC/USD", "score": 90, "category": "STRONG_BUY", "reasons": ["valid momentum"]},
                {"symbol": "BTC/USD", "score": 85, "category": "STRONG_BUY", "reasons": ["valid duplicate"]},
                {"symbol": "ETH/USD", "score": 99, "category": "STRONG_BUY", "reasons": ["fake signal"]},
            ]
        })

    def get_risk_summary(self):
        return Obj({"kill_switch_active": False})


class StockService:
    """No stock/options candidates."""

    def top_candidates(self, limit=10):
        return {"results": []}

    def top_options(self, limit=10):
        return {"top_candidates": []}


class Safety:
    """Passing safety."""

    def run(self):
        return Obj({"passed": True, "live_trading_locked": True, "no_add_order_detected": True, "no_withdrawal_methods_detected": True, "blockers": [], "warnings": []})


class Obj:
    """Object with to_dict."""

    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data


def test_daily_briefing_excludes_fake_signal_candidates_by_default() -> None:
    """Fake signals do not appear in daily briefing."""
    service = UnifiedReportService(dashboard_service=Dashboard(), stock_service=StockService(), safety_audit=Safety())

    briefing = service.get_daily_briefing()
    crypto = briefing["top_candidates"]["crypto"]

    assert len(crypto) == 1
    assert crypto[0]["symbol"] == "BTC/USD"
    assert all("fake" not in " ".join(candidate["reasons"]).lower() for candidate in crypto)
