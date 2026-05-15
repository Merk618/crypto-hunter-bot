# Crypto Hunter Bot

Crypto Hunter is a backend trading engine for a sophisticated crypto trading bot. This repository is intentionally backend-only and is designed to run independently. A separate application may connect to it later through FastAPI.

## Current Phase

Phase 1 foundation only:

- Clean Python backend project
- FastAPI health and status endpoints
- Pydantic settings
- Paper trading by default
- Live trading safety locks
- Exchange adapter interface
- Kraken adapter skeleton
- Coinbase placeholder adapter
- Basic risk and strategy shells

Live trading is not implemented yet.

## Safety Defaults

The default configuration is intentionally conservative:

- `BOT_MODE=paper`
- `ENABLE_LIVE_TRADING=false`
- `REQUIRE_LIVE_CONFIRMATION=true`
- `LiveBroker` refuses orders unless every live safety condition passes
- Exchange API secrets are never returned by API routes
- No withdrawal functionality exists in this repository

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

## Run Tests

```powershell
pytest
```

## Live Trading Warning

Live trading is locked down and not implemented in Phase 1. Kraken and Coinbase adapters do not place real live orders in this phase.
