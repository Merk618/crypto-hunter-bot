# Phase 36 Controlled Paper Review And Audit

Phase 36 adds read-only review, guardrail auditing, and local verification reporting for controlled paper observation.

It does not enable paper trading by default, does not start controlled paper observation, and does not add live trading.

## Why Phase 36 Exists

Phase 35 added controlled paper observation infrastructure. Phase 36 verifies that the infrastructure remains safe:

- controlled paper observation is disabled by default
- previews do not create paper trades
- disabled run-once records create zero paper trades
- controlled paper records are clearly paper-only
- `real_execution` remains false
- `live_trade` remains false
- broker labels remain `PAPER`

## Preview Versus Run-Once

Preview mode produces sizing and fee/slippage estimates only. It does not create paper orders or fills.

Run-once remains blocked by default because:

- controlled mode is disabled
- paper-trade observation is disabled
- buys are disabled
- operator approval and acknowledgement are required

## Paper-Only Labels

Any controlled paper records must be labeled:

- `mode="CONTROLLED_PAPER_OBSERVATION"`
- `broker="PAPER"`
- `real_execution=false`
- `live_trade=false`

## Guardrails Checked

The audit verifies:

- controlled paper is disabled by default
- buys are disabled by default
- sells remain disabled
- no live trades are detected
- no real execution is detected
- no non-PAPER broker records are detected
- preview records did not create trades
- disabled runs did not create trades
- paper-only labels are valid

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/review"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/audit"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/guardrails"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-review"
```

Existing controlled paper endpoints remain:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/recent"
```

## Live Trading Remains Blocked

Phase 36 does not add Kraken live order calls, MooMoo order/cancel/unlock methods, options execution, withdrawals, transfers, funding, staking, margin trading, or real broker execution.

## Next Recommendation

Use the review and audit endpoints after any local controlled paper preview/run-once checks. Continue requiring operator review and explicit future-phase approval before any paper-only observation execution is enabled.
