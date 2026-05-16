# Phase 15 Local Validation Checklist

This checklist validates Crypto Hunter locally with Kraken public data while live trading remains disabled.

## 1. Run Tests

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
.\.venv\Scripts\python.exe -m pytest
```

Expected result: all tests pass.

## 2. Start FastAPI

Open a dedicated PowerShell window:

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Keep this server running for the remaining checks.

## 3. Safety Audit

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/system/safety-audit"
```

Confirm:

- `passed` is `true`
- `live_trading_locked` is `true`
- `dangerous_config_detected` is `false`

## 4. Diagnostics Smoke Test

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/diagnostics/smoke-test"
```

Confirm:

- `live_trading_locked` is `true`
- `safety_audit_passed` is `true`
- failures, if any, are public-data availability warnings rather than live-trading failures

## 5. Calibration Report

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/diagnostics/calibration-report"
```

Confirm the `overall_status` is one of:

- `NORMAL`
- `TOO_STRICT`
- `TOO_LOOSE`
- `BLOCKED`
- `DATA_UNAVAILABLE`

Do not change thresholds from one scan.

## 6. Kraken Public Ticker

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/market/ticker/BTC-USD"
```

Confirm the response includes:

- `symbol`
- `bid`
- `ask`
- `last`
- `source`

## 7. Signal Checks

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/signals/BTC-USD?timeframe=1h&limit=250"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/signals/ETH-USD?timeframe=1h&limit=250"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/signals/SOL-USD?timeframe=1h&limit=250"
```

Confirm each available response includes:

- `score`
- `category`
- `risk_level`
- `reasons`
- `warnings`
- `blockers`
- `component_scores`

## 8. Dashboard Report

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/full-dashboard"
```

Confirm the response includes:

- `overview`
- `paper_performance`
- `signal_performance`
- `risk_summary`
- `recent_activity`
- `equity_curve`

## Validation Notes

- Kraken public-data failures may happen because of local network, DNS, or exchange availability.
- Private Kraken keys are not required for this checklist.
- No command in this checklist places a real order.
- Do not place a real order during Phase 15 validation.
- No command calls Kraken `AddOrder`.
- Live trading remains disabled.
