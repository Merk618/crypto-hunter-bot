"""Paper account tests."""

from app.portfolio.paper_account import PaperAccount


def test_paper_account_starts_with_default_cash() -> None:
    """Paper account starts with default cash."""
    account = PaperAccount()
    assert account.starting_cash == 10000.0
    assert account.cash_balance == 10000.0
    assert account.equity == 10000.0
