# Real-Data Validation - Phase 22

Phase 22 adds read-only validation tooling for running Crypto Hunter locally on your Windows machine with real Kraken public data and optional MooMoo/OpenD read-only data.

No trading is added. No live order, cancel, trade unlock, withdrawal, transfer, funding, staking, margin, or broker execution functionality is added.

## PowerShell Setup

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Safety Audit

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/system/safety-audit"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/startup-checks"
```

## Validation Scripts

Run these from the repo root:

```powershell
.\.venv\Scripts\python.exe scripts\validate_real_data_phase22.py
.\.venv\Scripts\python.exe scripts\validate_kraken_public.py
.\.venv\Scripts\python.exe scripts\validate_moomoo_readonly.py
```

`validate_real_data_phase22.py` exits with code 0 only if required checks pass. MooMoo checks may warn or fail cleanly when MooMoo is disabled or OpenD is disconnected.

## Validation Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/run"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/kraken"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/moomoo"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/report"
```

## Kraken Public Checks

No API keys are required.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/market/ticker/BTC-USD"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/market/candles/BTC-USD?timeframe=1h&limit=250"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/signals/BTC-USD?timeframe=1h&limit=250"
```

If Kraken is unavailable, check internet access, Kraken public API status, symbol spelling, and local firewall/VPN settings.

## MooMoo/OpenD Checks

MooMoo remains read-only. OpenD must be installed, running, and logged in for real MooMoo data.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/health"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/quote/AAPL"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/candles/AAPL?timeframe=1d&limit=250"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/options/AAPL"
```

If OpenD is disconnected, start OpenD, log in, confirm the default port `11111`, and rerun validation.

## Stock, Options, Alerts, Reports

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/top-candidates"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/options-scanner/top"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/alerts/preview"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/unified-summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/daily-briefing"
```

## Result Meaning

- `passed`: required checks passed.
- `warnings`: non-fatal issues, such as no candidates or MooMoo disabled.
- `blockers`: required checks failed and should be fixed before relying on local operation.

## Standalone-First

Crypto Hunter remains standalone-first in Phase 22. YucaTanaTrades integration is intentionally deferred until local real-data validation is reliable.
