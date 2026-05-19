# Phase 42 One-Command Health Check

The Phase 42 health check is a local, read-only verification command for Crypto Hunter v1.

## Run

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
.\.venv\Scripts\python.exe scripts\health_check_phase42.py
```

## What It Checks

- backend modules import
- config loads
- safety audit passes
- final safety review passes
- standalone readiness works
- v1 checklist works
- strategy checkpoint works
- signal quality review works
- controlled paper status is disabled
- controlled paper audit passes
- forbidden live order token is absent
- live trading is locked
- paper-trade observation is disabled
- secrets are not exposed

## Exit Code

- `0`: critical checks passed
- nonzero: at least one critical safety or readiness check failed

## Safety

This script does not place orders, does not enable paper trading, does not enable live trading, and does not mutate config, `.env`, journal rows, or legacy records.

## Related Scripts

```powershell
.\.venv\Scripts\python.exe scripts\operator_startup_check.py
.\.venv\Scripts\python.exe scripts\local_v1_smoke_test.py
```
