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
        quote={
            "last_price": 150,
            "ema_20": 145,
            "ema_50": 140,
            "ema_200": 120,
            "rsi": 55,
            "macd_line": 2.5,
            "macd_signal": 1.2,
            "volume": 2_000_000,
            "avg_volume": 1_000_000,
            "momentum_5d": 1.5,
            "momentum_20d": 4.0,
            "previous_close": 148,
            "bid": 149.9,
            "ask": 150.1,
        },
    )

    assert result.score >= 80
    assert result.category == "LEADING"
    assert result.trend_status == "BULLISH"
    assert result.volume_status == "HEALTHY"
