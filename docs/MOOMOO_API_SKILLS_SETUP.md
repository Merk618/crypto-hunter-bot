# MooMoo API And OpenD Setup

MooMoo integration starts read-only. This phase only checks package availability, OpenD configuration, and future feasibility.

## Requirements

MooMoo requires OpenD:

- OpenD must be installed.
- OpenD must be running.
- OpenD must be logged in.
- The default OpenD port is `11111`.
- Crypto Hunter defaults to `MOOMOO_ENABLED=false`, so socket checks are skipped unless explicitly enabled.

## Install Python Package

From the repo root:

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
.\.venv\Scripts\python.exe -m pip install moomoo-api --upgrade
```

## Import Test

```powershell
.\.venv\Scripts\python.exe -c "from moomoo import *; print('MooMoo API import OK')"
```

## Environment Values

```text
MOOMOO_ENABLED=false
MOOMOO_OPEND_HOST=127.0.0.1
MOOMOO_OPEND_PORT=11111
MOOMOO_READ_ONLY=true
MOOMOO_TRADING_ENABLED=false
MOOMOO_PAPER_TRADING_ENABLED=false
MOOMOO_UNLOCK_TRADE_CONTEXT=false
MOOMOO_ACCOUNT_ID=
MOOMOO_MARKET_REGION=US
```

## Safety Notes

- Trading remains disabled.
- Do not unlock trade context.
- Do not place stock orders.
- Do not place options orders.
- Do not enable margin trading.
- Do not add account funding, transfers, or withdrawals.
- This connector is for read-only feasibility checks only.

## API Checks

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/health"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/capabilities"
```
