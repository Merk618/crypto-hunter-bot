# Strategy Calibration Notes

Crypto Hunter uses transparent indicator scoring. Phase 15 does not change thresholds; it documents how to interpret calibration output.

## Current Score Categories

- `STRONG_BUY`: 80-100
- `BUY_WATCH`: 65-79
- `NEUTRAL`: 50-64
- `WEAK`: 35-49
- `AVOID_SELL`: 0-34

## Current Scoring Components

- Trend: 25 points
- Momentum: 25 points
- Volume/flow: 20 points
- Trend strength: 15 points
- Entry quality: 15 points

Total maximum: 100.

## RSI Interpretation

RSI uses period 14. The period is not a buy threshold.

- RSI below 30: oversold, possible bounce, but falling-knife risk
- RSI 35-40: early recovery but still weak
- RSI 40-60: ideal bullish momentum zone
- RSI 60-65: strong but slightly extended
- RSI 65-70: elevated; reduce score and avoid chasing
- RSI 70-75: overbought warning and trim/watch metadata
- RSI 75+: hard caution and long-entry score cap

For future exits:

- RSI 60-70 is not an automatic sell zone
- RSI 70-75 means watch for trim or tightened stop if momentum weakens
- RSI crossing down from above 70 is a sell/trim warning
- RSI crossing below 60 after being above 70 is a stronger momentum-exit warning
- RSI below 50 means bullish momentum is weakening
- RSI below 40 means bearish momentum

## Common Calibration Outcomes

### TOO_STRICT

The strategy rarely or never reaches `BUY_WATCH` or `STRONG_BUY`, even during normal bullish synthetic or historical examples.

Possible causes:

- trend filters are too restrictive
- blockers cap too many otherwise-valid signals
- minimum score for trade consideration is too high
- volume or ADX requirements are rejecting too many setups

### NORMAL

The strategy produces mostly `NEUTRAL`, `WEAK`, or `AVOID_SELL` in weak markets, and only produces `BUY_WATCH` or `STRONG_BUY` when trend, momentum, volume, and risk context agree.

This is the desired default.

### TOO_LOOSE

The strategy produces `STRONG_BUY` during weak trend, high risk, low volume, or obvious blocker conditions.

Possible causes:

- blockers are not capping score enough
- risk-level metadata is too permissive
- volume/ADX requirements are too weak
- entry-quality scoring is overpowering trend weakness

### BLOCKED

Signals exist, but explicit blockers prevent clean long-entry interpretation.

Common blockers:

- close at or below EMA 200
- MACD line below signal
- ATR missing or invalid
- volume missing or zero
- ADX below 15
- RSI greater than or equal to 75

### DATA_UNAVAILABLE

Market data, candles, indicators, or signal generation were unavailable.

This can happen because:

- Kraken public API was unavailable
- local network access was blocked
- the symbol is unavailable
- too few candles were returned

## When To Consider Threshold Changes

Do not change thresholds from one scan.

Only consider adjustments after reviewing:

- multiple market sessions
- multiple symbols
- bullish, bearish, and sideways environments
- Phase 14 smoke-test output
- calibration reports
- backtest results
- paper-trading behavior
- risk rejections and blockers

Threshold changes should be small, documented, and covered by tests.

## What Not To Do

- Do not lower thresholds just to force trades.
- Do not remove blockers without understanding why they fired.
- Do not treat RSI 70 as an automatic sell.
- Do not tune only on BTC if the watchlist includes ETH, SOL, SUI, XRP, LINK, or AVAX.
- Do not use paper results as proof of live performance.
