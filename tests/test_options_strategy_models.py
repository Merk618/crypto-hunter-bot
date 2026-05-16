"""Options scanner model tests."""

from app.stock_hunter.options_strategy_models import OptionsScanRequest, RankedOptionContract


def test_options_scan_request_applies_default_filters() -> None:
    """Request defaults come from safe scanner settings."""
    request = OptionsScanRequest(symbols=["aapl", "MSFT"])

    assert request.symbols == ["AAPL", "MSFT"]
    assert request.option_type == "call"
    assert request.min_volume == 500
    assert request.min_open_interest == 1000
    assert request.max_spread_pct == 8
    assert request.delta_min == 0.50
    assert request.delta_max == 0.60
    assert request.min_dte == 14
    assert request.max_dte == 90
    assert request.target_dte_min == 21
    assert request.target_dte_max == 60
    assert request.top_n == 10


def test_ranked_option_contract_includes_scoring_fields() -> None:
    """Ranked contracts serialize all scoring fields."""
    contract = RankedOptionContract(
        rank=1,
        symbol="AAPL260619C00150000",
        underlying="AAPL",
        expiration="2026-06-19",
        dte=35,
        strike=150,
        option_type="call",
        bid=4.9,
        ask=5.1,
        mid=5.0,
        last=5.0,
        volume=1000,
        open_interest=2000,
        implied_volatility=0.3,
        delta=0.55,
        gamma=None,
        theta=None,
        vega=None,
        spread_pct=4.0,
        liquidity_score=80,
        contract_score=85,
        underlying_score=75,
        total_score=81,
        label="RESEARCH_CANDIDATE",
        reasons=[],
        warnings=[],
        blockers=[],
    )

    data = contract.to_dict()
    assert data["source"] == "stock_hunter_ranked_option_v1"
    assert data["total_score"] == 81
    assert data["underlying_score"] == 75
