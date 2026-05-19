# Crypto Hunter Handoff Package

This package is for operating Crypto Hunter standalone v1 locally.

## Project Path

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
```

## Start Backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Stop with `Ctrl+C` in the terminal running Uvicorn.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Health Check

```powershell
.\.venv\Scripts\python.exe scripts\health_check_phase42.py
```

## Key Endpoints

- `GET /operator/v1-startup-guide`
- `GET /operator/one-command-health-check`
- `GET /audit/v1-freeze-report`
- `GET /operator/v1-handoff-package`
- `GET /operator/future-roadmap`
- `GET /operator/next-project-plan`
- `GET /strategy/review-checkpoint`
- `GET /observation/signal-quality`
- `GET /observation/controlled-paper/status`

## Intentionally Disabled

- Live crypto trading
- Paper-trade observation
- Controlled paper observation
- MooMoo execution
- Options execution
- Strategy threshold mutation
- Legacy journal mutation

## Do Not Change Without Review

- Live trading flags
- Controlled paper flags
- Minimum signal score thresholds
- EMA 200 trade requirement
- Journal rows or legacy risk records

## Resume Later

1. Run the Phase 42 health check.
2. Review `/strategy/review-checkpoint`.
3. Review `/observation/signal-quality`.
4. Collect more persisted observations before any future paper-mode discussion.

