"""Phase 18 options liquidity and DTE scoring tests."""

from datetime import date

from app.config import Settings
from app.stock_hunter.options_chain_analyzer import OptionsChainAnalyzer


def analyzer() -> OptionsChainAnalyzer:
    """Create deterministic analyzer with fixed date."""
    return OptionsChainAnalyzer(Settings(_env_file=None), today=date(2026, 5, 15))


def contract(**overrides) -> dict:
    """Return a liquid baseline contract."""
    data = {
        "symbol": "AAPL260619C00150000",
        "underlying": "AAPL",
        "expiration": "2026-06-19",
        "strike": 150,
        "option_type": "call",
        "bid": 4.9,
        "ask": 5.1,
        "last": 5,
        "volume": 1200,
        "open_interest": 2500,
        "implied_volatility": 0.35,
        "delta": 0.55,
    }
    data.update(overrides)
    return data


def test_options_analyzer_calculates_dte() -> None:
    """DTE is calculated from expiration."""
    result = analyzer().analyze("AAPL", [contract()])

    assert result.best_call_candidates[0]["dte"] == 35


def test_options_analyzer_rejects_too_short_dte() -> None:
    """Contracts below the DTE minimum are rejected."""
    result = analyzer().analyze("AAPL", [contract(expiration="2026-05-20")])

    assert result.rejected_contracts_count == 1


def test_options_analyzer_rejects_too_long_dte() -> None:
    """Contracts above the DTE maximum are rejected."""
    result = analyzer().analyze("AAPL", [contract(expiration="2026-12-18")])

    assert result.rejected_contracts_count == 1


def test_options_analyzer_prefers_target_dte() -> None:
    """Target DTE contracts receive strong scores."""
    result = analyzer().analyze("AAPL", [contract()])

    candidate = result.best_call_candidates[0]
    assert candidate["candidate_label"] == "RESEARCH_CANDIDATE"
    assert candidate["contract_score"] >= 80


def test_options_analyzer_scores_volume_open_interest_spread_delta() -> None:
    """Contract scoring includes liquidity and delta fields."""
    result = analyzer().analyze("AAPL", [contract()])
    candidate = result.best_call_candidates[0]

    assert candidate["liquidity_score"] > 0
    assert candidate["spread_pct"] <= 8
    assert "delta in target range" in candidate["reasons"]


def test_options_analyzer_ranks_best_call_candidates() -> None:
    """Higher-quality call candidates are ranked first."""
    weaker = contract(symbol="AAPL260619C00155000", volume=600, open_interest=1200, bid=4.5, ask=5.1)
    stronger = contract(symbol="AAPL260619C00150000", volume=5000, open_interest=8000, bid=4.95, ask=5.05)
    result = analyzer().analyze("AAPL", [weaker, stronger])

    assert result.best_call_candidates[0]["symbol"] == "AAPL260619C00150000"


def test_options_analyzer_handles_missing_greeks_cleanly() -> None:
    """Missing greeks do not crash analysis."""
    result = analyzer().analyze("AAPL", [contract(delta=None, gamma=None, theta=None, vega=None)])

    assert result.rejected_contracts_count == 1
    assert result.best_call_candidates == []
