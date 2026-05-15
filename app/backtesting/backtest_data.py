"""Backtest data helpers."""

from __future__ import annotations

import json

import pandas as pd


def load_csv_candles(path: str) -> pd.DataFrame:
    """Load candle CSV with timestamp/open/high/low/close/volume."""
    df = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing CSV candle columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return dataframe_from_kraken_candles(df)


def save_backtest_result(result, path: str) -> None:
    """Save a backtest result JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict() if hasattr(result, "to_dict") else result, f, indent=2)


def dataframe_from_kraken_candles(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize OHLCV candles into engine-ready format."""
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    for column in ["open", "high", "low", "close", "volume"]:
        out[column] = pd.to_numeric(out[column], errors="raise").astype(float)
    if "vwap" not in out.columns:
        out["vwap"] = (out["high"] + out["low"] + out["close"]) / 3
    if "count" not in out.columns:
        out["count"] = 1
    if "symbol" not in out.columns:
        out["symbol"] = "UNKNOWN"
    if "exchange_symbol" not in out.columns:
        out["exchange_symbol"] = out["symbol"]
    return out
