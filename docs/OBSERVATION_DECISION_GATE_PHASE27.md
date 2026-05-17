# Observation Decision Gate Phase 27

Phase 27 fixes observation-window accounting and adds a read-only strategy decision gate. The gate reviews paper observation and calibration results, then recommends the next safe operational step without changing thresholds or enabling trading.

## Bugfix Summary

Observation windows now distinguish:

- completed observation runs
- refused or interval-blocked attempts
- total attempted runs

Refused runs no longer increment `completed_runs`, and window summaries count only completed runs in `runs_analyzed`.

## Why Refused Runs Should Not Count

Interval-blocked or lower-level refused runs do not generate a valid market-data/signal/risk sample. Counting them as completed would distort calibration readiness and make the sample look stronger than it is.

## Early Recovery Watchlist

The early recovery classifier is observation-only. A symbol can be tagged when it repeatedly shows:

- score from `EARLY_RECOVERY_MIN_SCORE` to `EARLY_RECOVERY_MAX_SCORE`
- NEUTRAL or watch-like category
- EMA 200 blocker
- momentum evidence such as MACD, ADX, OBV, RSI recovery-zone, or positive momentum component
- risk not approved
- action remains `OBSERVE_ONLY`

This is not a buy signal and does not permit paper or live execution.

## Decision Gate States

- `KEEP_OBSERVING`: sample is too small or no higher-confidence pattern is present
- `ADD_EARLY_RECOVERY_WATCHLIST`: repeated neutral candidates are EMA 200 blocked but show momentum evidence
- `ALLOW_PAPER_TRADE_OBSERVATION`: reserved for future paper-only review after repeated STRONG_BUY/risk-approved observations
- `READY_FOR_TINY_LIVE_REVIEW`: defined as a future state but remains unreachable in this phase
- `BLOCKED`: safety audit failed

## EMA 200 Remains Required

The gate may recommend an early recovery watchlist tag, but it does not recommend removing the EMA 200 requirement for trade execution. The trend filter remains conservative by design.

## Live Review Remains Blocked

`ALLOW_LIVE_REVIEW=false` by default and is validated as false. Live trading, Kraken AddOrder, MooMoo trade unlock, options execution, withdrawals, transfers, funding, staking, margin, and broker execution remain unavailable.

## Endpoint Examples

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/decision-gate"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/decision-gate"
```

## Next Phase

Continue observation-only windows and review whether early recovery candidates repeat across multiple market sessions. Any future paper-trade observation permission should stay manual, paper-only, and gated behind repeated STRONG_BUY/risk-approved evidence.

