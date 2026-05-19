# Crypto Hunter V1 Freeze

Phase 43 marks Crypto Hunter standalone v1 as ready to freeze when the local safety checks and test suite pass.

## Current Status

- Standalone backend: ready for local operation
- Live trading: disabled
- Paper-trade observation: disabled
- Controlled paper observation: disabled
- Real exchange execution: absent
- Kraken live order placement: absent
- Strategy threshold auto-apply: disabled
- EMA 200 trade requirement: retained

## Freeze Verification

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\health_check_phase42.py
Invoke-RestMethod -Uri "http://127.0.0.1:8000/audit/v1-freeze-report" | ConvertTo-Json -Depth 10
```

Expected result:

- `v1_status=READY_TO_FREEZE`
- `ready_to_archive_as_v1=true`
- `live_trading_enabled=false`
- `paper_trading_enabled=false`
- `controlled_paper_enabled=false`
- `add_order_absent=true`
- `real_execution_absent=true`

## Recommended Tag

```powershell
git tag v1.0.0-standalone-observation
git push origin v1.0.0-standalone-observation
```

Tag only after the operator confirms tests and the one-command health check are green.

## What V1 Means

Crypto Hunter v1 is an observation-first local backend. It provides market data, signal analysis, risk gates, journals, observation windows, calibration reports, early recovery watchlists, controlled-paper guardrails, audits, runbooks, and reporting endpoints.

It does not enable paper trading or live trading by default.

