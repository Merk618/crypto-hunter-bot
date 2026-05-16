"""Unified report service tests."""

from app.config import Settings
from app.reporting.unified_report_service import UnifiedReportService


class EmptyDashboard:
    """Empty dashboard fake."""

    def get_overview(self):
        """Return empty overview."""
        return Obj({"paper_equity": 0})

    def get_signal_performance(self, limit=100):
        """Return no signals."""
        return Obj({"recent_signals": []})

    def get_risk_summary(self):
        """Return risk summary."""
        return Obj({"kill_switch_active": False})


class CandidateDashboard(EmptyDashboard):
    """Dashboard with crypto signal."""

    def get_signal_performance(self, limit=100):
        """Return crypto signals."""
        return Obj({"recent_signals": [{"symbol": "BTC/USD", "score": 90, "category": "STRONG_BUY", "reasons": [], "warnings": [], "blockers": []}]})


class StockService:
    """Fake stock/options service."""

    def top_candidates(self, limit=10):
        """Return stock candidates."""
        return {"results": [{"symbol": "AAPL", "opportunity_score": 86, "stock_signal": {"symbol": "AAPL", "score": 86, "category": "LEADING", "reasons": [], "warnings": [], "blockers": []}}]}

    def top_options(self, limit=10):
        """Return option candidates."""
        return {"top_candidates": [{"symbol": "AAPL260619C00150000", "underlying": "AAPL", "option_type": "call", "total_score": 80, "label": "RESEARCH_CANDIDATE", "reasons": [], "warnings": [], "blockers": []}]}


class Safety:
    """Fake safety audit."""

    def run(self):
        """Return passing safety."""
        return Obj({"passed": True, "live_trading_locked": True, "no_add_order_detected": True, "no_withdrawal_methods_detected": True, "blockers": [], "warnings": []})


class Obj:
    """Object with to_dict."""

    def __init__(self, data: dict) -> None:
        self.data = data

    def to_dict(self) -> dict:
        return self.data


def test_unified_report_service_returns_empty_default_clean_response() -> None:
    """Empty optional data does not crash."""
    service = UnifiedReportService(settings=Settings(_env_file=None), dashboard_service=EmptyDashboard(), stock_service=StockService(), safety_audit=Safety())

    summary = service.get_unified_dashboard_summary()

    assert "top_candidates" in summary
    assert "risk_safety" in summary


def test_unified_report_service_summarizes_top_candidates() -> None:
    """Top candidates include crypto, stock, and option data."""
    service = UnifiedReportService(settings=Settings(_env_file=None), dashboard_service=CandidateDashboard(), stock_service=StockService(), safety_audit=Safety())

    top = service.get_top_candidates()

    assert top["crypto"][0]["symbol"] == "BTC/USD"
    assert top["stocks"][0]["symbol"] == "AAPL"
    assert top["options"][0]["symbol"] == "AAPL260619C00150000"


def test_unified_report_service_includes_safety_status() -> None:
    """System health includes safety status."""
    service = UnifiedReportService(settings=Settings(_env_file=None), dashboard_service=EmptyDashboard(), stock_service=StockService(), safety_audit=Safety())

    health = service.get_system_health_summary()

    assert health["safety"]["passed"] is True
