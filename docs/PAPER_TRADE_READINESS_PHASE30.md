# Paper Trade Readiness Phase 30

Phase 30 adds a read-only readiness gate for deciding whether Crypto Hunter could be reviewed for paper-trade observation in a future phase.

It does not enable paper trades, live trades, or real exchange execution.

## Purpose

The readiness gate answers:

- Is the safety audit passing?
- Is live trading locked?
- Is Kraken AddOrder absent?
- Is there enough persisted observation history?
- Were any STRONG_BUY signals observed?
- Did risk manager approve any observations?
- Are risk decision records internally consistent?
- Are early recovery candidates still observe-only?
- Would operator approval be required before any future paper-trade observation?

## Early Recovery Is Not Paper Trading

Early recovery candidates are still:

- `OBSERVE_ONLY`
- `NOT A TRADE SIGNAL`
- `EMA 200 BLOCKED`

EMA 200 remains required for trade execution. Phase 30 does not loosen strategy thresholds.

## Risk Record Hygiene

Risk hygiene scans recent journaled risk decisions and flags records such as:

- `approved=false` with `approved_quantity > 0`
- `approved=false` with `max_quantity > 0`
- `approved=false` with `risk_amount > 0`
- `approved=true` with blockers
- missing symbol or side
- malformed reasons, warnings, or blockers

Hygiene is preview-only. It does not delete or mutate journal records.

## Readiness Decisions

- `NOT_READY`: required evidence is missing
- `OBSERVE_ONLY`: enough observation exists for watchlist/review, but not paper-trade observation
- `READY_FOR_PAPER_TRADE_OBSERVATION_REVIEW`: reserved for a future phase with stronger evidence and operator approval
- `BLOCKED`: safety or hygiene blocker exists

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/inconsistencies"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/readiness"
```

## Why Paper Trades Remain Disabled

Current evidence may show early recovery candidates, but paper-trade observation requires repeated STRONG_BUY signals and clean risk approvals. Phase 30 only validates readiness and operator approval structure.

Default:

```env
PAPER_TRADE_OBSERVATION_ALLOW_ENABLE=false
PAPER_TRADE_OBSERVATION_REQUIRE_OPERATOR_APPROVAL=true
```

## Next Phase

Continue observation-only windows. If clean STRONG_BUY and risk-approved observations eventually appear, add a separate future phase for explicit operator-reviewed paper-trade observation.

