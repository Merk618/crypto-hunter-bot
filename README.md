# Crypto Hunter Bot

Crypto Hunter is a backend trading engine for a sophisticated crypto trading bot. This repository is intentionally backend-only and is designed to run independently. A separate application may connect to it later through FastAPI.

## Current Phase

Phase 5 safe paper trading foundation:

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

Use `BTC-USD` in path parameters because raw `BTC/USD` contains a slash and is not path-safe. The API converts `BTC-USD` to `BTC/USD` internally.

Manual paper buy example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/paper/order" -ContentType "application/json" -Body '{"symbol":"BTC/USD","side":"buy","quantity":0.01,"market_price":65000,"reason":"manual paper test"}'
```

Manual paper close example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/paper/close/BTC-USD" -ContentType "application/json" -Body '{"market_price":66000,"reason":"manual paper close test"}'
```

## Run Tests

```powershell
pytest
```

## Live Trading Warning

Live trading is locked down and not implemented in Phase 5. Private exchange APIs, real order placement, live sell execution, and Coinbase integration are not implemented in this phase.
