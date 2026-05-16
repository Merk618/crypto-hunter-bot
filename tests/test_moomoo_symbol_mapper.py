"""MooMoo symbol mapper tests."""

import pytest

from app.connectors.moomoo.moomoo_symbol_mapper import MooMooSymbolError, MooMooSymbolMapper


def test_symbol_mapper_converts_aapl_to_provider_symbol() -> None:
    """Common stock symbols get a US prefix."""
    assert MooMooSymbolMapper().to_provider_symbol("AAPL") == "US.AAPL"


def test_symbol_mapper_keeps_prefixed_symbol_unchanged() -> None:
    """Already-prefixed symbols are preserved."""
    assert MooMooSymbolMapper().to_provider_symbol("US.AAPL") == "US.AAPL"


def test_symbol_mapper_rejects_crypto_symbols() -> None:
    """Crypto pairs do not belong in Stock Hunter."""
    mapper = MooMooSymbolMapper()

    with pytest.raises(MooMooSymbolError):
        mapper.to_provider_symbol("BTC/USD")


def test_symbol_mapper_rejects_invalid_symbols() -> None:
    """Invalid equity symbols are rejected."""
    with pytest.raises(MooMooSymbolError):
        MooMooSymbolMapper().to_provider_symbol("BAD SYMBOL!")
