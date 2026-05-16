# Standalone Operator Layer - Phase 21

Phase 21 keeps Crypto Hunter standalone-first. It adds operator-focused status, startup checks, command summaries, scripts, and runbook endpoints. YucaTanaTrades frontend embedding is intentionally deferred until the standalone backend proves reliable.

## Run Standalone

From PowerShell:

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Stop the local server with `Ctrl+C`.

## Operator Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/startup-checks"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/commands"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/daily-briefing"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/next-actions"
```

## Scripts

```powershell
.\.venv\Scripts\python.exe scripts\operator_status.py
.\.venv\Scripts\python.exe scripts\operator_smoke_check.py
.\.venv\Scripts\python.exe scripts\operator_daily_briefing.py
```

These scripts call internal read-only services and print local JSON summaries.

## Daily Workflow

1. Run the test suite.
2. Start the backend locally.
3. Check `/operator/startup-checks`.
4. Check `/system/safety-audit`.
5. Review `/operator/daily-briefing`.
6. Review `/alerts/preview`.
7. Review stock and options candidates if MooMoo is available.

## Safety

Phase 21 adds no trading. It does not place crypto trades, stock trades, options orders, MooMoo orders, Kraken AddOrder calls, cancels, withdrawals, transfers, funding, staking, margin trades, or broker executions.

Kraken public reachability is not checked by `/operator/status` by default because that endpoint avoids network calls. Use diagnostics or market endpoints manually when you want a live public-data check.

## Future YucaTanaTrades Integration

YucaTanaTrades integration should happen later, after standalone operator checks, startup checks, alerts, paper trading, reports, and safety audits are stable under local use.
