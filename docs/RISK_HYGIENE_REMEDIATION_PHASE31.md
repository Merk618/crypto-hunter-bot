# Phase 31 Risk Hygiene Remediation

Phase 31 fixes risk-decision persistence hygiene and adds preview-only tools for classifying older inconsistent journal records. It does not delete records, enable paper trades, enable live trading, or add any exchange execution.

## What Was Found

Paper-trade readiness found rejected risk records that still carried approval-only values:

- `approved=false` with `approved_quantity > 0`
- `approved=false` with `max_quantity > 0`
- `approved=false` with `risk_amount > 0`
- `approved=false` with `estimated_notional > 0`

These fields can make rejected decisions look partially approved in reports. Rejected records should keep their reasons, warnings, and blockers, but approval-only quantity and risk fields must be null.

## Forward Fix

Before a rejected risk decision is persisted, the journal serialization path now normalizes it:

- `approved_quantity=null`
- `max_quantity=null`
- `risk_amount=null`
- `estimated_notional=null`

Approved risk decisions may still persist approval quantities, max quantities, risk amounts, and estimated notionals.

## Legacy Versus Current Records

Risk hygiene classifies records as:

- `LEGACY_INCONSISTENT_REJECTED_RECORD`
- `CURRENT_INCONSISTENT_REJECTED_RECORD`
- `CLEAN_REJECTED_RECORD`
- `CLEAN_APPROVED_RECORD`
- `MALFORMED_RECORD`

Legacy records are preserved for audit history. They are not deleted or modified automatically. Current inconsistent records block paper-trade observation readiness.

## Preview-Only Remediation

Phase 31 adds a remediation preview that explains what should be reviewed without mutating the database. Destructive cleanup remains disabled by default:

- `RISK_HYGIENE_PREVIEW_ONLY=true`
- `RISK_HYGIENE_ALLOW_DESTRUCTIVE_CLEANUP=false`

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/inconsistencies"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/classification"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/remediation-preview"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/recent-cleanliness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-readiness"
```

## Readiness Impact

Paper-trade observation remains conservative. It stays blocked or not ready when:

- there are no repeated `STRONG_BUY` observations
- there are no risk-approved observations
- current/recent risk records are inconsistent
- safety audit or live-lock checks fail

Early recovery candidates remain observe-only. EMA 200 remains required for trade execution.

## Safety

Phase 31 does not add Kraken live order calls, MooMoo order/cancel/unlock methods, options execution, withdrawals, transfers, funding, staking, margin trading, paper-trade enablement, or live trading.
