"""Reporting performance summary helpers."""

from __future__ import annotations


def calculate_return_pct(starting_equity: float, ending_equity: float) -> float:
    """Calculate return percentage safely."""
    if starting_equity <= 0:
        return 0.0
    return ((ending_equity - starting_equity) / starting_equity) * 100


def calculate_basic_win_rate_from_fills_or_trades(data: list[dict]) -> float | None:
    """Calculate win rate when PnL-bearing records are available."""
    pnl_values = [float(item["net_pnl"]) for item in data if item.get("net_pnl") is not None]
    if not pnl_values:
        pnl_values = [float(item["realized_pnl"]) for item in data if item.get("realized_pnl") is not None]
    if not pnl_values:
        return None
    return (sum(1 for pnl in pnl_values if pnl > 0) / len(pnl_values)) * 100


def calculate_profit_factor_from_closed_trades(data: list[dict]) -> float | None:
    """Calculate profit factor from records with PnL values."""
    pnl_values = [float(item["net_pnl"]) for item in data if item.get("net_pnl") is not None]
    if not pnl_values:
        pnl_values = [float(item["realized_pnl"]) for item in data if item.get("realized_pnl") is not None]
    if not pnl_values:
        return None
    wins = sum(pnl for pnl in pnl_values if pnl > 0)
    losses = abs(sum(pnl for pnl in pnl_values if pnl < 0))
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return wins / losses


def summarize_orders(orders: list[dict]) -> dict:
    """Summarize order records."""
    return {"total_orders": len(orders), "buy_orders": sum(1 for order in orders if order.get("side") == "buy"), "sell_orders": sum(1 for order in orders if order.get("side") == "sell")}


def summarize_fills(fills: list[dict]) -> dict:
    """Summarize fill records."""
    return {"total_fills": len(fills), "total_fees": sum(float(fill.get("fee") or 0) for fill in fills)}


def summarize_signals(signals: list[dict]) -> dict:
    """Summarize signal categories and scores."""
    categories = [signal.get("category") for signal in signals]
    scores = [float(signal.get("score") or 0) for signal in signals]
    return {
        "total_signals": len(signals),
        "strong_buy_count": categories.count("STRONG_BUY"),
        "buy_watch_count": categories.count("BUY_WATCH"),
        "neutral_count": categories.count("NEUTRAL"),
        "weak_count": categories.count("WEAK"),
        "avoid_sell_count": categories.count("AVOID_SELL"),
        "average_score": sum(scores) / len(scores) if scores else 0.0,
    }


def rank_symbols_by_latest_signal(signals: list[dict]) -> list[dict]:
    """Rank symbols by their latest available score."""
    latest_by_symbol = {}
    for signal in reversed(signals):
        symbol = signal.get("symbol")
        if symbol and symbol not in latest_by_symbol:
            latest_by_symbol[symbol] = {"symbol": symbol, "score": signal.get("score", 0), "category": signal.get("category"), "created_at": signal.get("created_at")}
    return sorted(latest_by_symbol.values(), key=lambda row: row.get("score") or 0, reverse=True)
