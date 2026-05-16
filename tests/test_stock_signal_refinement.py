"""Phase 18 refined stock signal scoring tests."""

from app.stock_hunter.stock_signal_engine import StockSignalEngine


def bullish_quote(rsi: float = 55) -> dict:
    """Return deterministic bullish quote data."""
    return {
        "latest_price": 150,
        "ema_20": 145,
        "ema_50": 135,
        "ema_200": 110,
        "rsi": rsi,
        "macd_line": 3,
        "macd_signal": 1,
        "volume": 2_000_000,
        "avg_volume": 1_000_000,
        "momentum_5d": 2,
        "momentum_20d": 8,
        "previous_close": 148,
        "bid": 149.9,
        "ask": 150.1,
    }


def test_refined_stock_signal_scores_bullish_data_as_leading_or_watch() -> None:
    """Bullish quote data earns a strong research score."""
    result = StockSignalEngine().score("AAPL", quote=bullish_quote())

    assert result.category in {"LEADING", "WATCH"}
    assert result.score >= 65
    assert result.raw_score is not None
    assert result.component_scores["trend"] > 0


def test_refined_stock_signal_scores_weak_data_as_weak_or_avoid() -> None:
    """Weak trend and momentum data receives a low score."""
    result = StockSignalEngine().score(
        "AAPL",
        quote={
            "latest_price": 90,
            "ema_20": 95,
            "ema_50": 100,
            "ema_200": 120,
            "rsi": 32,
            "macd_line": -1,
            "macd_signal": 1,
            "volume": 100_000,
            "avg_volume": 1_000_000,
            "momentum_5d": -3,
            "momentum_20d": -10,
            "previous_close": 100,
        },
    )

    assert result.category in {"WEAK", "AVOID"}
    assert result.trend_status == "WEAK"


def test_rsi_overextended_warns_and_caps_at_watch() -> None:
    """RSI above the extended threshold warns and prevents LEADING category."""
    result = StockSignalEngine().score("AAPL", quote=bullish_quote(rsi=80))

    assert result.category != "LEADING"
    assert any("RSI overextended" in warning for warning in result.warnings)


def test_missing_candle_and_quote_data_returns_clean_blocker() -> None:
    """Unavailable data returns a structured blocker."""
    result = StockSignalEngine().score("AAPL")

    assert result.category == "AVOID"
    assert result.trend_status == "DATA_UNAVAILABLE"
    assert result.blockers


def test_component_scores_are_included() -> None:
    """All Phase 18 component scores are included."""
    result = StockSignalEngine().score("AAPL", quote=bullish_quote())

    assert set(result.component_scores) == {"trend", "momentum", "volume_liquidity", "market_quality", "options_support"}
    assert result.source == "stock_hunter_signal_v2"
