# Phase 39 Signal Quality Review And Observation Continuation

Phase 39 adds read-only analysis for persisted observation results. It explains why observations are not reaching `STRONG_BUY` or risk-approved status yet, summarizes dominant blockers, highlights early recovery candidates, and produces the next safest observation plan.

This phase does not change thresholds, enable paper trades, enable live trading, or mutate journal/config data.

## Why No STRONG_BUY Means Observe-Only

Controlled paper observation is not appropriate without repeated `STRONG_BUY` signals and clean risk-approved observations. If scores remain `WEAK` or `NEUTRAL`, the correct behavior is to continue observing and collecting evidence.

## Dominant Blockers

The signal quality report counts repeated blockers across persisted completed observation runs. If EMA 200 is dominant, that means the trend filter is doing its job. EMA 200 remains required for trade execution.

## Early Recovery Vs Trade Readiness

Early recovery candidates can show improving or neutral-range behavior while still blocked by trend filters. They are:

- `OBSERVE_ONLY`
- not trade signals
- not paper-trade approvals
- not live-trade approvals

## Thresholds

Phase 39 may recommend manual review of scoring components, but it always returns:

- `threshold_change_recommended=false`
- `paper_trade_observation_recommended=false`
- `live_review_recommended=false`

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/signal-quality"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/signal-quality/symbols"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/signal-quality/BTC-USD"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/continuation-plan"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/signal-quality-review"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/observation-next-step"
```

## Recommended Next Steps

Continue persisted observation windows until repeated `STRONG_BUY` and risk-approved observations appear. Review dominant blockers manually, keep thresholds unchanged, and keep EMA 200 required for execution.
