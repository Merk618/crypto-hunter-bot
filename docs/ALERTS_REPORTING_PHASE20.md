# Alerts and Unified Reporting - Phase 20

Phase 20 adds read-only alert previews and unified reporting polish for Crypto Hunter, Stock Hunter, and Options Scanner.

No trading is added. No external alert is sent by default. Discord remains dry-run only in this phase.

## Purpose

The alert/reporting layer produces clean summaries for:

- Top crypto candidates
- Top stock candidates
- Top options candidates
- Risk status
- Safety status
- Daily briefing data

## Alert Thresholds

Defaults:

- `ALERT_MIN_CRYPTO_SCORE=80`
- `ALERT_MIN_STOCK_SCORE=80`
- `ALERT_MIN_OPTIONS_SCORE=75`
- `ALERT_MAX_ITEMS_PER_SECTION=10`

Alerts are disabled by default:

- `ALERTS_ENABLED=false`
- `ALERTS_READ_ONLY=true`
- `ALERT_CHANNEL_DISCORD=false`
- `ALERT_CHANNEL_EMAIL=false`

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/alerts/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/alerts/preview"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/alerts/send-console"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/alerts/send-discord-dry-run"
```

Unified reports:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/unified-summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/top-candidates"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/daily-briefing"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/system-health"
```

## Discord Dry-Run

`POST /alerts/send-discord-dry-run` formats the alert payload but never calls a webhook. Webhook URLs are not returned by API responses.

## Safety

This phase is reporting and formatting only. It does not place crypto trades, stock trades, options orders, MooMoo orders, Kraken AddOrder calls, cancels, withdrawals, transfers, funding, staking, margin trades, or broker executions.

Future real notification delivery should be added only after explicit safety review and secret-handling tests.
