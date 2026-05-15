# Crypto Hunter Bot

Crypto Hunter is a backend trading engine for a sophisticated crypto trading bot. This repository is intentionally backend-only and is designed to run independently. A separate application may connect to it later through FastAPI.

## Current Phase

Phase 10 reporting and dashboard API:

- Clean Python backend project
- FastAPI health and status endpoints
- Pydantic settings
- Paper trading by default
- Live trading safety locks
- Exchange adapter interface
- Kraken public REST market data for AssetPairs, Ticker, OHLC, and Depth
- Coinbase placeholder adapter
- Basic risk and strategy shells
- Indicator engine for candle DataFrames from Phase 2
- Transparent signal scoring and explanation from indicator-enhanced candles
- Safe in-memory paper trading with balances, positions, fees, slippage, realized PnL, and unrealized PnL
- Risk validation, position sizing, cooldown controls, and kill-switch controls
- Manual paper auto-trading scans that combine market data, signals, risk checks, and paper buys
- SQLite trade journal for bot events, signals, risk decisions, paper orders/fills/positions, account snapshots, scan results, and errors
- Offline backtesting engine with trades, equity curve, drawdown, win rate, fees, slippage, and performance metrics
- Read-only reporting API for dashboard overview, paper performance, signal quality, risk status, recent activity, and equity curves

Live trading and real exchange order execution are not implemented yet.

## Indicators

Phase 3 calculates:

- EMA 20, EMA 50, EMA 200
- RSI 14
- MACD line, signal, and histogram
- Bollinger Bands 20 with 2 standard deviations
- ATR 14
- OBV, OBV slope 5, and positive OBV trend flag
- ADX 14, plus DI, and minus DI
- Volume SMA 20 and volume-above-SMA flag

## Signal Categories

- `STRONG_BUY`: 80-100
- `BUY_WATCH`: 65-79
- `NEUTRAL`: 50-64
- `WEAK`: 35-49
- `AVOID_SELL`: 0-34

Hard blockers can cap score or category even when raw component scores are high.

## RSI Interpretation

RSI uses period 14. The period is not a buy threshold.

- RSI below 30: oversold with falling-knife risk
- RSI 35-40: early recovery but still weak
- RSI 40-60: ideal bullish momentum zone
- RSI 60-65: strong but slightly extended
- RSI 65-70: elevated; reduce score and avoid chasing
- RSI 70-75: overbought warning and trim/watch metadata
- RSI 75+: hard caution and long-entry score cap

For future exits, RSI 60-70 is not an automatic sell zone. RSI crossing down from above 70, or below 60 after being above 70, is advisory exit metadata only.

## Scoring Breakdown

- Trend: 25 points
- Momentum: 25 points
- Volume/flow: 20 points
- Trend strength: 15 points
- Entry quality: 15 points

Signals include reasons, warnings, blockers, component scores, suggested ATR-based levels, and advisory exit metadata. They do not place or simulate trades.

## Paper Trading

Phase 5 adds manual paper trading only. It simulates trades from explicit market prices supplied by the caller. It does not auto-trade signals and does not send orders to an exchange.

Defaults:

- `PAPER_STARTING_CASH=10000`
- `PAPER_FEE_RATE=0.0025` means 0.25%
- `PAPER_SLIPPAGE_BPS=10` means 10 bps, or 0.10%

Buy fills use `market_price * (1 + slippage_bps / 10000)`.
Sell fills use `market_price * (1 - slippage_bps / 10000)`.

Paper trading is useful for validating mechanics, but it does not guarantee live performance.

## Risk Management

Phase 6 adds a risk decision layer. It does not execute trades. It only approves or rejects proposed trades.

Risk checks include:

- Minimum signal score and `STRONG_BUY` category requirement
- Signal blockers
- Buy/sell side validation
- Market price validation
- Available cash
- Maximum open positions
- Maximum single-position allocation
- Daily realized loss limit
- Spread limit
- Kill switch status
- Symbol cooldowns
- Maximum trades per day
- Consecutive loss limit

## Position Sizing

The risk sizer uses:

```text
risk_amount = equity * MAX_RISK_PER_TRADE
risk_per_unit = abs(entry_price - stop_loss_price)
quantity = risk_amount / risk_per_unit
```

Then quantity is capped by available cash and maximum allocation.

## Kill Switch

The kill switch can be manually activated or triggered after repeated API failures:

- `MAX_API_FAILURES_BEFORE_KILL=5`
- active kill switch rejects all risk evaluations

## Cooldowns

Cooldowns are symbol-specific and timestamp-based:

- `COOLDOWN_AFTER_TRADE_MINUTES=15`
- `COOLDOWN_AFTER_LOSS_MINUTES=60`

Cooldowns only block risk approval. They do not execute or close positions.

## Paper Auto-Trading

Phase 7 adds a manual paper auto-trading loop. It scans configured symbols, generates signals, evaluates risk, and places paper buy orders only when every condition passes.

Defaults:

- `PAPER_AUTO_TRADING_ENABLED=false`
- `PAPER_ALLOW_AUTOBUY=true`
- `PAPER_ALLOW_AUTOSELL=false`
- `BOT_SCAN_TIMEFRAME=1h`
- `BOT_SCAN_LIMIT=250`
- `BOT_MIN_SECONDS_BETWEEN_SCANS=60`

`/bot/start` does not create an infinite blocking loop. Use `/bot/scan-once` to run a manual scan. Auto-selling is disabled by default and no real orders are ever placed.

## SQLite Trade Journal

Phase 8 adds durable SQLite persistence so paper activity can be reviewed after restart.

Defaults:

- `DATABASE_URL=sqlite:///./crypto_hunter.db`
- `ENABLE_TRADE_JOURNAL=true`

Stored records:

- bot events
- signal records
- risk decisions
- paper orders
- paper fills
- paper position snapshots
- account snapshots
- scan results
- error records

API keys and secret-looking payload fields are scrubbed before JSON payloads are stored.

## Backtesting

Phase 9 adds offline backtesting from historical candle DataFrames or JSON candles. It never calls private exchange APIs and never places orders.

Anti-lookahead rule:

- A signal generated on candle `N` can only execute on candle `N+1`.
- The default simulated execution price is the next candle open.

Assumptions:

- Long-only; shorts are disabled by default.
- Entry requires `STRONG_BUY`, minimum score, no hard blockers, and price above EMA 200.
- Exits can occur from stop loss, take profit, bearish MACD, losing EMA 20 after profit, RSI overbought cross-down, or the final candle.
- Buy slippage: `price * (1 + slippage_bps / 10000)`.
- Sell slippage: `price * (1 - slippage_bps / 10000)`.
- Fee: `notional * fee_rate`.

Backtests are research tools. They do not guarantee future performance.

## Reporting API

Phase 10 adds clean JSON reporting endpoints for a future YucaTanaTrades frontend. These endpoints are read-only: they do not start the bot, scan markets, place paper orders, or touch live exchange APIs.

Reports summarize:

- bot state
- paper account performance
- signal category quality
- risk and kill-switch status
- recent journal activity
- account-snapshot equity curve
- full dashboard snapshot

The reporting layer is designed as an API boundary that YucaTanaTrades can later consume without coupling directly to bot internals.

## Safety Defaults

The default configuration is intentionally conservative:

- `BOT_MODE=paper`
- `ENABLE_LIVE_TRADING=false`
- `REQUIRE_LIVE_CONFIRMATION=true`
- `LiveBroker` refuses orders unless every live safety condition passes
- Exchange API secrets are never returned by API routes
- No withdrawal functionality exists in this repository
- Phase 2/3 use Kraken public endpoints and local indicator calculations only; no API keys are required for indicators

## Setup

```powershell
cd crypto-hunter-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Run Locally

```powershell
uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/status`
- `http://127.0.0.1:8000/market/symbols`
- `http://127.0.0.1:8000/market/ticker/BTC-USD`
- `http://127.0.0.1:8000/market/candles/BTC-USD?timeframe=1h&limit=200`
- `http://127.0.0.1:8000/signals/BTC-USD?timeframe=1h&limit=250`
- `http://127.0.0.1:8000/signals/watchlist?timeframe=1h&limit=250`
- `http://127.0.0.1:8000/paper/account`
- `http://127.0.0.1:8000/paper/positions`
- `http://127.0.0.1:8000/paper/orders`
- `http://127.0.0.1:8000/paper/fills`
- `http://127.0.0.1:8000/risk/status`
- `http://127.0.0.1:8000/bot/status`
- `http://127.0.0.1:8000/journal/events`
- `http://127.0.0.1:8000/journal/signals`
- `http://127.0.0.1:8000/journal/risk-decisions`
- `http://127.0.0.1:8000/journal/orders`
- `http://127.0.0.1:8000/journal/fills`
- `http://127.0.0.1:8000/journal/positions`
- `http://127.0.0.1:8000/journal/account-snapshots`
- `http://127.0.0.1:8000/journal/scans`
- `http://127.0.0.1:8000/journal/errors`
- `http://127.0.0.1:8000/backtest/single`
- `http://127.0.0.1:8000/backtest/watchlist`
- `http://127.0.0.1:8000/reports/overview`
- `http://127.0.0.1:8000/reports/paper-performance`
- `http://127.0.0.1:8000/reports/signal-performance`
- `http://127.0.0.1:8000/reports/risk-summary`
- `http://127.0.0.1:8000/reports/recent-activity`
- `http://127.0.0.1:8000/reports/equity-curve`
- `http://127.0.0.1:8000/reports/full-dashboard`

Use `BTC-USD` in path parameters because raw `BTC/USD` contains a slash and is not path-safe. The API converts `BTC-USD` to `BTC/USD` internally.

Manual paper buy example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/paper/order" -ContentType "application/json" -Body '{"symbol":"BTC/USD","side":"buy","quantity":0.01,"market_price":65000,"reason":"manual paper test"}'
```

Manual paper close example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/paper/close/BTC-USD" -ContentType "application/json" -Body '{"market_price":66000,"reason":"manual paper close test"}'
```

Risk evaluation example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/risk/evaluate" -ContentType "application/json" -Body '{"symbol":"BTC/USD","side":"buy","market_price":65000,"spread_bps":12,"requested_quantity":null,"signal_result":{"score":84,"category":"STRONG_BUY","blockers":[],"suggested_stop_loss":63000,"suggested_entry":65000}}'
```

Kill switch examples:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/risk/kill-switch/activate" -ContentType "application/json" -Body '{"reason":"manual safety pause"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/risk/kill-switch/deactivate" -ContentType "application/json" -Body '{"reason":"resume testing"}'
```

Manual paper bot scan:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/bot/start" -ContentType "application/json" -Body '{"manual_start":true}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/bot/scan-once"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/bot/stop"
```

Journal initialization and reads:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/journal/init"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/orders?limit=20&symbol=BTC/USD"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/scans?limit=20"
```

Backtest with JSON candles:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/backtest/single" -ContentType "application/json" -Body '{"symbol":"BTC/USD","timeframe":"1h","candles":[{"timestamp":"2026-01-01T00:00:00Z","open":65000,"high":66000,"low":64000,"close":65500,"volume":100}]}'
```

Reporting examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/overview"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/full-dashboard"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/equity-curve?limit=500"
```

## Run Tests

```powershell
pytest
```

## Live Trading Warning

Live trading is locked down and not implemented in Phase 10. Private exchange APIs, real order placement, live sell execution, and Coinbase integration are not implemented in this phase. Reporting is read-only, and paper/backtest results do not guarantee live performance.
