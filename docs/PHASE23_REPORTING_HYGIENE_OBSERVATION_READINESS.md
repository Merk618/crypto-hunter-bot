# Phase 23 Reporting Hygiene and Observation Readiness

Phase 23 cleans production-style reports and adds readiness checks before long-running paper observation mode.

No trading is added. No records are deleted automatically. Hygiene tools are preview-first.

## Why Filter Fake/Test Records

Local test runs and development fixtures can leave records such as `fake signal`, mock records, demo records, dry-run records, and backtest records in the journal. Those are useful for tests, but they should not appear in production-style daily briefings.

Production reports now exclude records that look like:

- fake/test/mock/demo/sample/dummy records
- backtest records
- dry-run records
- malformed warning/blocker-only artifacts

## Hygiene Tools

Endpoints:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/hygiene/summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/hygiene/test-records"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/hygiene/production-preview"
```

These endpoints do not delete records. They only classify, normalize, filter, and preview.

## Daily Briefing Behavior

`GET /reports/daily-briefing` uses production-style candidate filtering by default:

- fake/test/demo candidates are excluded
- duplicate candidates are deduped by asset class and symbol
- malformed persisted warning/blocker fields are normalized

## Observation Readiness

Endpoint:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/readiness"
```

The readiness checker verifies:

- safety audit passes
- live trading is locked
- Kraken public data works
- crypto signal generation works
- paper account is available
- journal is available
- reports are not polluted with fake/test data
- operator layer is available
- alerts are dry-run/read-only
- no real execution paths exist

MooMoo disabled is a warning for crypto-only observation, not a blocker.

## Next Phase

The next natural phase is paper observation mode: a long-running, paper-only observation process that periodically records market snapshots, signals, and report outputs without placing real orders.

## Safety

Phase 23 does not place crypto trades, stock trades, options orders, MooMoo orders, Kraken AddOrder calls, cancels, withdrawals, transfers, funding, staking, margin trades, or broker executions.
