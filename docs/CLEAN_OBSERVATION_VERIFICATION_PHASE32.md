# Phase 32 Clean Observation Verification

Phase 32 verifies that Phase 31 risk hygiene remediation is working on new observation data. It also separates current risk record corruption from legacy audit history so paper-trade readiness is easier to interpret.

No records are deleted, mutated, rewritten, or hidden. No paper trades or live trades are enabled.

## Why This Phase Exists

Phase 31 fixed future risk decision persistence so rejected decisions no longer carry approval-only fields such as:

- `approved_quantity`
- `max_quantity`
- `risk_amount`
- `estimated_notional`

Existing legacy records can still contain old inconsistent values. Phase 32 keeps those legacy records visible as audit warnings while ensuring current inconsistent records still block readiness.

## Current Versus Legacy Risk Hygiene

Current inconsistent records:

- indicate the forward-fix may not be working
- block paper-trade observation readiness
- require investigation before any future paper-trade observation review

Legacy inconsistent records:

- remain in the journal for audit history
- are reported separately
- warn by default
- are not deleted or automatically rewritten

Default behavior:

- `RISK_HYGIENE_LEGACY_RECORDS_WARN_ONLY=true`
- `RISK_HYGIENE_REQUIRE_CURRENT_CLEANLINESS=true`
- `PAPER_TRADE_OBSERVATION_ALLOW_ENABLE=false`

## Clean Observation Verification

The clean verifier checks recent persisted completed observation runs and their risk decisions:

- rejected decisions should classify as `CLEAN_REJECTED_RECORD`
- approved decisions should classify as `CLEAN_APPROVED_RECORD`
- current inconsistent rejected records should be absent
- legacy inconsistent records should be reported as warnings

If not enough post-Phase31 observations exist, the verifier returns an insufficient-data response.

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/clean-verification"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/legacy-aware-readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/recent-cleanliness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-readiness"
```

## Readiness Interpretation

Expected conservative behavior:

- current risk inconsistencies block
- legacy inconsistencies warn
- no `STRONG_BUY` observations means paper-trade observation remains not ready
- no risk-approved observations means paper-trade observation remains not ready
- paper-trade observation remains disabled by config
- live review remains unavailable

## Next Recommendation

Run additional observation windows after Phase 31, then check:

- `/observation/clean-verification`
- `/risk/hygiene/legacy-aware-readiness`
- `/observation/paper-trade-readiness`

Only after repeated clean observations, repeated `STRONG_BUY` signals, and clean risk approvals should a future paper-trade observation review phase be considered. Live trading remains out of scope.
