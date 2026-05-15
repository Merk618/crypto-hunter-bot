# Crypto Hunter Bot

Crypto Hunter is a backend trading engine for a sophisticated crypto trading bot. This repository is intentionally backend-only and is designed to run independently. A separate application may connect to it later through FastAPI.

## Current Phase

Phase 3 indicator engine foundation:

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

Signals and live trading are not implemented yet.

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

Use `BTC-USD` in path parameters because raw `BTC/USD` contains a slash and is not path-safe. The API converts `BTC-USD` to `BTC/USD` internally.

## Run Tests

```powershell
pytest
```

## Live Trading Warning

Live trading is locked down and not implemented in Phase 3. Signal scoring, paper trading, order placement, and Coinbase integration are not implemented in this phase.
