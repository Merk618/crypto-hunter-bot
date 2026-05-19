# Phase 40 Strategy Review Checkpoint

Phase 40 adds a formal strategy checkpoint and extended observation plan. It combines signal-quality review, calibration, early recovery, controlled-paper decision, paper-trade readiness, fresh validation, risk hygiene, and safety audit status into one operator-facing review.

This phase is review and planning only. It does not change thresholds, enable paper trades, enable live trading, or mutate config/journal data.

## Why Phase 40 Exists

Crypto Hunter needs a clean checkpoint before any future paper-trade observation review. The checkpoint answers whether the strategy is still observe-only, needs a larger observation window, needs manual signal component review, or is blocked by safety/guardrail issues.

## No STRONG_BUY Means Observe-Only

If no persisted observations have reached `STRONG_BUY`, the system should keep observing. Early recovery candidates are useful for monitoring but are not trade signals.

## EMA 200 Remains Required

When EMA 200 is a dominant blocker, the trend filter is still protecting the system. Phase 40 may recommend manual review of trend behavior, but it does not remove EMA 200 as a trade requirement.

## Extended Observation Plan

Use the plan to collect a larger persisted observation window:

- target additional runs
- target additional observations
- focus symbols
- success criteria
- stop conditions
- review questions
- recommended local commands

The plan is always observe-only in this phase.

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/strategy/review-checkpoint"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/strategy/extended-observation-plan"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/strategy/review-package"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/strategy-review"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/extended-observation-next-step"
```

## Safety

Phase 40 keeps:

- `threshold_change_recommended=false`
- `paper_trade_recommended=false`
- `live_review_recommended=false`
- `paper_trades_allowed=false`
- `live_review_allowed=false`

## Next Recommendation

Run an extended persisted observation window, then review the strategy checkpoint again. Do not enable paper or live trading from Phase 40 output.
