"""Options chain analyzer tests."""

from app.config import Settings
from app.stock_hunter.options_chain_analyzer import OptionsChainAnalyzer


def contract(**overrides) -> dict:
    """Create a valid baseline option contract."""
    data = {
        "symbol": "AAPL260116C00150000",
        "underlying": "AAPL",
        "expiration": "2026-01-16",
        "strike": 150,
        "option_type": "call",
        "bid": 4.9,
        "ask": 5.1,
        "last": 5.0,
        "volume": 1000,
        "open_interest": 2000,
        "implied_volatility": 0.3,
        "delta": 0.55,
    }
    data.update(overrides)
    return data


def analyzer() -> OptionsChainAnalyzer:
    """Create deterministic analyzer."""
    return OptionsChainAnalyzer(Settings(_env_file=None))


def test_options_analyzer_filters_by_volume() -> None:
    """Low volume contracts are rejected."""
    result = analyzer().analyze("AAPL", [contract(volume=100)])

    assert result.rejected_contracts_count == 1
    assert result.best_call_candidates == []


def test_options_analyzer_filters_by_open_interest() -> None:
    """Low open interest contracts are rejected."""
    result = analyzer().analyze("AAPL", [contract(open_interest=100)])

    assert result.rejected_contracts_count == 1


def test_options_analyzer_filters_by_bid_ask_spread() -> None:
    """Wide spreads are rejected."""
    result = analyzer().analyze("AAPL", [contract(bid=1, ask=2)])

    assert result.rejected_contracts_count == 1


def test_options_analyzer_filters_by_delta_range() -> None:
    """Call delta must fit target range."""
    result = analyzer().analyze("AAPL", [contract(delta=0.8)])

    assert result.rejected_contracts_count == 1


def test_options_analyzer_returns_best_candidates() -> None:
    """Valid contracts are returned as research candidates."""
    put = contract(symbol="AAPL260116P00150000", option_type="put", delta=-0.45)
    result = analyzer().analyze("AAPL", [contract(), put])

    assert result.contracts_analyzed == 2
    assert len(result.best_call_candidates) == 1
    assert len(result.best_put_candidates) == 1
    assert result.best_call_candidates[0]["liquidity_score"] > 0
