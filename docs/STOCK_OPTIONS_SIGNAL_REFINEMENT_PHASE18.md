# Stock/Options Signal Refinement - Phase 18

Phase 18 refines the read-only Stock/Options Hunter research layer. It does not place orders, unlock MooMoo trade context, execute options, cancel orders, or touch Kraken live-trading locks.

## Stock Scoring

Stock signals use deterministic component scores:

- Trend, 30 points: close above EMA 200, EMA 50, EMA 20, plus EMA alignment.
- Momentum, 25 points: RSI zone, MACD bullish state, 5-day momentum, and 20-day momentum.
- Volume/liquidity, 20 points: volume above 20-period average, average volume floor, dollar volume, and price above 5.
- Market/quality, 15 points: acceptable spread, normal/open market state, non-extreme gap, and fresh-enough data.
- Options support, 10 points: liquid call candidates, target-delta candidates, and acceptable option spreads.

Categories:

- `LEADING`: 80-100
- `WATCH`: 65-79
- `NEUTRAL`: 50-64
- `WEAK`: 35-49
- `AVOID`: 0-34

RSI between 40 and 65 is preferred. RSI from 65 to 75 adds an elevated warning. RSI at or above 75 caps a signal below `LEADING`.

## Options Liquidity

Options are classified for research only:

- `RESEARCH_CANDIDATE`
- `WATCHLIST_CANDIDATE`
- `REJECTED`

Filters include:

- Volume at least `STOCK_HUNTER_MIN_OPTION_VOLUME`.
- Open interest at least `STOCK_HUNTER_MIN_OPTION_OPEN_INTEREST`.
- Bid/ask spread at or below `STOCK_HUNTER_MAX_BID_ASK_SPREAD_PCT`.
- Valid bid/ask with bid above zero.
- Call delta inside `STOCK_HUNTER_TARGET_DELTA_MIN` to `STOCK_HUNTER_TARGET_DELTA_MAX`.

## DTE Rules

- Reject contracts with DTE below `STOCK_HUNTER_OPTIONS_MIN_DTE`.
- Reject contracts with DTE above `STOCK_HUNTER_OPTIONS_MAX_DTE`.
- Prefer DTE between `STOCK_HUNTER_OPTIONS_TARGET_DTE_MIN` and `STOCK_HUNTER_OPTIONS_TARGET_DTE_MAX`.

## Scanner Ranking

The scanner combines the stock signal score and best call research-candidate score:

```text
opportunity_score = stock_score * 0.75 + best_call_contract_score * 0.25
```

Results are sorted highest first and assigned a rank. The scanner remains read-only and returns `RESEARCH_ONLY`, `WATCH_ONLY`, or `NO_ACTION`.

## Endpoint Examples

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/scan"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/top-candidates"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/analyze/AAPL"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/options/AAPL"
```

MooMoo remains read-only. Options execution is not implemented. No real broker orders are possible in this phase.
