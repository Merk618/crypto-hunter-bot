"""Stock signal engine tests."""

from app.stock_hunter.stock_signal_engine import StockSignalEngine


def test_stock_signal_engine_returns_unavailable_when_data_missing() -> None:
    """Missing quote/candle data returns clean unavailable result."""
    result = StockSignalEngine().score("AAPL")

    assert result.category == "AVOID"
    assert result.trend_status == "DATA_UNAVAILABLE"
    assert result.blockers


def test_stock_signal_engine_scores_mock_bullish_data() -> None:
    """Bullish mock data can score as leading."""
    result = StockSignalEngine().score(
        "AAPL",
        quote={"last_price": 150, "moving_average": 140, "volume": 2_000_000, "avg_volume": 1_000_000, "momentum": 1.5},
    )

    assert result.score >= 80
    assert result.category == "LEADING"
    assert result.trend_status == "BULLISH"
    assert result.volume_status == "ABOVE_AVERAGE"
