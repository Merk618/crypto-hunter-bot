# Phase 33 Fresh Observation Validation

Phase 33 adds a fresh observation-window validation layer. It proves that new completed observation runs created after the Phase 31/32 risk hygiene fixes produce clean persisted risk decisions.

This phase is read-only validation and reporting. It does not enable paper trades, live trading, real exchange execution, options execution, or any cleanup mutation.

## Why Phase 33 Exists

Phase 31 normalized future rejected risk decisions before persistence. Phase 32 separated current risk corruption from legacy audit warnings. Phase 33 verifies fresh observation windows against those rules:

- new rejected decisions should classify as `CLEAN_REJECTED_RECORD`
- new approved decisions, if any, should classify as `CLEAN_APPROVED_RECORD`
- current inconsistent rejected records should be absent
- legacy inconsistent records remain visible as warnings only

## Running A Fresh Two-Run Observation Window

Start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Start a manual observation window:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/start" -ContentType "application/json" -Body '{"target_runs":2,"allow_paper_trades":false}'
```

Run the first observation:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/run-next" -ContentType "application/json" -Body '{"manual_run":true,"ignore_interval":true}'
```

Run the second observation:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/run-next" -ContentType "application/json" -Body '{"manual_run":true,"ignore_interval":true}'
```

Check fresh validation:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/fresh-validation"
```

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/fresh-validation"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/fresh-validation/runs"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/fresh-validation/readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/fresh-observation-check"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/legacy-aware-readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-readiness"
```

## Reading The Report

Possible statuses:

- `INSUFFICIENT_DATA`: not enough completed runs or persisted results
- `BLOCKED_CURRENT_RISK_INCONSISTENCY`: new/current risk records are inconsistent
- `PASSED`: enough fresh records exist and current risk records are clean

Legacy warnings do not fail validation when `FRESH_OBSERVATION_ALLOW_LEGACY_WARNINGS=true`.

## Important Safety Note

Passing fresh validation does not enable paper trading or live trading.

Paper-trade readiness still requires future explicit criteria such as repeated `STRONG_BUY` observations and clean risk approvals. Live trading remains locked and out of scope.

## Next Recommendation

Run a fresh two-run observation window, review `/observation/fresh-validation`, and confirm `/observation/paper-trade-readiness` remains conservative. Continue collecting observation evidence before any future paper-trade observation phase.
