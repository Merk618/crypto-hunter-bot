"""Phase 29 safety and unified report tests."""

import inspect

from app.connectors.moomoo.moomoo_readonly_client import MooMooReadOnlyClient
from app.main import app
from app.reporting.unified_report_service import UnifiedReportService
from tests.test_early_recovery_watchlist import run


class FakeWatchlist:
    """Fake early recovery service."""

    def __init__(self, *args, **kwargs):
        pass

    def get_report(self):
        return {
            "candidates": [
                {
                    "symbol": "SUI/USD",
                    "rank": 1,
                    "latest_score": 61,
                    "average_score": 56.2,
                    "repeated_count": 5,
                    "dominant_blockers": ["close at or below EMA 200"],
                    "warnings": [],
                    "reason": "observe only",
                    "action": "OBSERVE_ONLY",
                }
            ]
        }


def test_unified_report_includes_observe_only_early_recovery_section(monkeypatch) -> None:
    """Unified report includes early recovery section."""
    import app.reporting.unified_report_service as module

    monkeypatch.setattr(module, "EarlyRecoveryWatchlistService", FakeWatchlist)
    top = UnifiedReportService().get_top_candidates()

    assert top["early_recovery"][0]["symbol"] == "SUI/USD"
    assert "NOT A TRADE SIGNAL" in top["early_recovery"][0]["warnings"]


def test_no_kraken_add_order_added_phase29() -> None:
    """No Kraken AddOrder route was added."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "addorder" not in paths
    assert "add_order" not in paths


def test_no_moomoo_order_cancel_unlock_methods_added_phase29() -> None:
    """MooMoo client remains read-only."""
    names = " ".join(name.lower() for name, _ in inspect.getmembers(MooMooReadOnlyClient))

    assert "place_order" not in names
    assert "submit_order" not in names
    assert "cancel" not in names
    assert "unlock" not in names


def test_no_options_execution_fund_movement_live_or_paper_trading_enabled_phase29() -> None:
    """No execution or fund movement routes exist."""
    paths = " ".join(route.path.lower() for route in app.routes)

    assert "options-execution" not in paths
    assert "execute-option" not in paths
    assert "withdraw" not in paths
    assert "transfer" not in paths
    assert "funding" not in paths
    assert "staking" not in paths
    assert "live-order" not in paths

