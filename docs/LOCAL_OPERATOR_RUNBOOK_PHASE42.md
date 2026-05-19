# Phase 42 Local Operator Runbook

Phase 42 makes Crypto Hunter v1 easy to start, verify, operate locally, and hand off. It does not enable paper trading, controlled paper observation, live trading, threshold changes, or real exchange execution.

## Start Backend

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Leave this terminal open while using the API.

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## One-Command Health Check

```powershell
.\.venv\Scripts\python.exe scripts\health_check_phase42.py
```

## Operator Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/local-runbook"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/one-command-health-check"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/local-smoke-test"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/v1-startup-guide"
```

## Safety Checks

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/system/safety-audit"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/audit/final-safety-review"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/audit/standalone-readiness"
```

## Strategy And Observation Checks

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/strategy/review-checkpoint"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/strategy/extended-observation-plan"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/signal-quality"
```

## Controlled Paper Disabled Check

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/audit"
```

## Stop Backend

Press `Ctrl+C` in the uvicorn terminal.

## Troubleshooting

- If endpoints fail, confirm uvicorn is running.
- If safety audit fails, stop and resolve blockers before continuing.
- If market data is unavailable, use validation endpoints to distinguish local app readiness from public API availability.
- Do not enable paper or live trading from this runbook.
