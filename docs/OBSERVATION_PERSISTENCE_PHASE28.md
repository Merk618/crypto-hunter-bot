# Observation Persistence Phase 28

Phase 28 makes observation intelligence survive backend restarts. Observation runs and results are persisted to the existing SQLite journal, then hydrated back into calibration reports, decision gates, early recovery candidates, and observation reports.

## Why In-Memory State Is Insufficient

Phase 26/27 observation sessions kept recent runs in memory. After a backend restart, decision endpoints could lose the 20-observation evidence base and return `observations_analyzed=0`.

Phase 28 fixes that by storing completed observation history in SQLite.

## What Gets Persisted

Observation run metadata:

- `run_id`
- `started_at`
- `completed_at`
- `status`
- `symbols_requested`
- `symbols_processed`
- `signals_generated`
- `risk_decisions_generated`
- `paper_trades_created`
- `warnings`
- `blockers`
- `source`

Observation result records:

- `run_id`
- `symbol`
- `timeframe`
- signal payload
- risk decision payload
- paper trade result payload, if any
- `action_taken`
- `reasons`
- `warnings`
- `blockers`
- `observed_at`
- `source`

Payloads are passed through the journal serializers, which scrub secret-like keys.

## Hydration

`ObservationHydrationService` loads persisted history and reconstructs observation run dictionaries for:

- `/calibration/report`
- `/calibration/decision-gate`
- `/observation/decision-gate`
- `/observation/early-recovery`
- `/observation/report`

If active in-memory session data exists, endpoints use it. If memory is empty after restart, endpoints fall back to persisted completed observations.

## Refused Runs

Refused runs may be persisted for audit, but they do not count toward:

- calibration reports
- decision gates
- early recovery candidates
- observation window summaries

Use `include_refused=true` on history endpoints only when diagnostics require it.

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history/runs"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history/results"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history/summary"
```

Decision gate after restart:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/decision-gate"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery"
```

## Restart Resilience

Expected behavior:

- If persisted completed observations exist, decision gates hydrate and analyze them.
- If no history exists, decision gates return clean `KEEP_OBSERVING`.
- `live_review_allowed` remains false.
- `paper_trade_observation_allowed` remains false unless future explicit rules allow it.

## Safety

Phase 28 does not add live trading, Kraken AddOrder, real exchange execution, MooMoo trading, options execution, fund movement, or automatic threshold changes.

## Next Phase

Run another observation window after restart, verify the hydrated history remains available, then review whether an observation-only early recovery tag deserves a visible operator workflow.

