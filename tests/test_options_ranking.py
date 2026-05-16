"""Options ranking engine tests."""

from app.stock_hunter.options_ranking import OptionsRankingEngine


def contract(**overrides) -> dict:
    """Return a ranked-contract input."""
    data = {
        "symbol": "AAPL260619C00150000",
        "underlying": "AAPL",
        "expiration": "2026-06-19",
        "dte": 35,
        "strike": 150,
        "option_type": "call",
        "bid": 4.9,
        "ask": 5.1,
        "last": 5.0,
        "volume": 1000,
        "open_interest": 2000,
        "implied_volatility": 0.3,
        "delta": 0.55,
        "spread_pct": 4.0,
        "liquidity_score": 80,
        "contract_score": 80,
        "reasons": [],
        "warnings": [],
        "blockers": [],
    }
    data.update(overrides)
    return data


def test_ranking_engine_ranks_higher_liquidity_contracts_higher() -> None:
    """Liquidity contributes to total ranking."""
    ranked = OptionsRankingEngine().rank_contracts(
        [contract(symbol="LOW", liquidity_score=20), contract(symbol="HIGH", liquidity_score=90)],
        underlying_score=80,
    )

    assert ranked[0].symbol == "HIGH"


def test_ranking_engine_penalizes_wide_spreads() -> None:
    """Wide spreads reduce total score."""
    tight = OptionsRankingEngine().rank_contract(contract(symbol="TIGHT", spread_pct=1.0), underlying_score=80)
    wide = OptionsRankingEngine().rank_contract(contract(symbol="WIDE", spread_pct=8.0), underlying_score=80)

    assert tight.total_score > wide.total_score


def test_ranking_engine_rewards_target_delta() -> None:
    """Target delta improves adjusted contract score."""
    target = OptionsRankingEngine().rank_contract(contract(delta=0.55), underlying_score=80)
    outside = OptionsRankingEngine().rank_contract(contract(delta=0.25), underlying_score=80)

    assert target.contract_score > outside.contract_score


def test_ranking_engine_rewards_target_dte() -> None:
    """Target DTE improves total score."""
    target = OptionsRankingEngine().rank_contract(contract(dte=35), underlying_score=80)
    acceptable = OptionsRankingEngine().rank_contract(contract(dte=80), underlying_score=80)

    assert target.total_score > acceptable.total_score


def test_ranking_engine_includes_underlying_score() -> None:
    """Underlying score participates in total score."""
    high = OptionsRankingEngine().rank_contract(contract(), underlying_score=90)
    low = OptionsRankingEngine().rank_contract(contract(), underlying_score=40)

    assert high.total_score > low.total_score
    assert high.underlying_score == 90
