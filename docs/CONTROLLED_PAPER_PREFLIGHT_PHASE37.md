# Phase 37 Controlled Paper Activation Preflight

Phase 37 adds a read-only preflight layer for future controlled paper observation activation. It determines whether the system is eligible for manual operator config review, but it does not enable paper trades, mutate files, or place orders.

## Why Phase 37 Exists

Controlled paper observation has several prior safety layers:

- audit: verifies guardrails and paper-only labels
- review: summarizes controlled paper records
- readiness: checks observation/risk evidence
- approval: packages operator review criteria
- preflight: decides whether a future manual config review is even reasonable

## Status Meanings

- `DISABLED`: preflight itself is disabled
- `BLOCKED`: safety, audit, review, or current risk hygiene failed
- `NOT_READY`: data or approval evidence is incomplete
- `OBSERVE_ONLY`: safe to keep observing, but missing `STRONG_BUY` or risk-approved evidence
- `READY_FOR_OPERATOR_CONFIG_REVIEW`: all checks pass, but no trades are enabled
- `READY_BUT_NOT_ENABLED`: reserved for future use

## Ready Does Not Mean Enabled

`READY_FOR_OPERATOR_CONFIG_REVIEW` means a human can review a future paper-only activation plan. It still returns:

- `paper_trade_execution_allowed_now=false`
- `live_review_allowed=false`
- `config_change_required=true`

The activation plan is read-only and does not edit `.env`, config, journal rows, or legacy records.

## Activation Plan

The plan lists:

- required manual steps
- required config flags for a future paper-only test
- flags that must remain false
- max notional per trade
- max trades per run
- max trades per day
- safety warnings
- rollback steps

Live trading flags must remain false.

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/preflight"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/preflight/checks"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/activation-plan"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/preflight-package"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-preflight"
```

## Live Trading Remains Blocked

Phase 37 does not add Kraken live order calls, MooMoo order/cancel/unlock methods, options execution, withdrawals, transfers, funding, staking, margin trading, or real broker execution.

## Next Recommendation

Continue observation-only mode until the preflight moves from `OBSERVE_ONLY` or `NOT_READY` to `READY_FOR_OPERATOR_CONFIG_REVIEW`. Even then, use the activation plan only for manual review in a future phase.
