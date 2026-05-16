"""Alert model tests."""

from app.alerts.alert_models import AlertCandidate


def test_alert_candidate_serializes_crypto_candidate() -> None:
    """Crypto candidate serializes."""
    candidate = AlertCandidate("crypto", "BTC/USD", "BTC signal", 88, "STRONG_BUY")

    assert candidate.to_dict()["asset_class"] == "crypto"


def test_alert_candidate_serializes_stock_candidate() -> None:
    """Stock candidate serializes."""
    candidate = AlertCandidate("stock", "AAPL", "AAPL stock", 82, "LEADING")

    assert candidate.to_dict()["symbol"] == "AAPL"


def test_alert_candidate_serializes_option_candidate() -> None:
    """Option candidate serializes."""
    candidate = AlertCandidate("option", "AAPL260619C00150000", "AAPL call", 79, "RESEARCH_CANDIDATE")

    assert candidate.to_dict()["category"] == "RESEARCH_CANDIDATE"
