# Early Recovery Watchlist Phase 29

Phase 29 adds an observation-only Early Recovery Watchlist powered by persisted observation history.

## What Early Recovery Means

An early recovery candidate is a crypto symbol that repeatedly appears in the neutral recovery score band while still blocked by the EMA 200 trend filter. It may show momentum evidence, but it is not eligible for trade execution.

Typical evidence:

- score between `EARLY_RECOVERY_MIN_SCORE` and `EARLY_RECOVERY_MAX_SCORE`
- repeated observations
- NEUTRAL or watch-like category
- EMA 200 blocker
- momentum evidence from MACD, ADX, OBV, RSI, or the momentum component
- risk remains unapproved

## Observe Only

Every watchlist item is labeled:

- `action="OBSERVE_ONLY"`
- `trade_allowed=false`
- `paper_trade_allowed=false`
- `live_trade_allowed=false`

This watchlist does not enable paper trades, live trades, or any order path.

## EMA 200 Still Blocks Trade Execution

The watchlist is a research view. EMA 200 remains required for actual trade execution. Phase 29 does not remove or weaken the EMA 200 requirement.

## Ranking Rules

Candidates are ranked by:

1. average score
2. repeated count
3. max score
4. latest score

The default max candidates is:

```env
EARLY_RECOVERY_MAX_CANDIDATES=10
```

## Endpoint Examples

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/watchlist"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/report"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/SUI-USD"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/report"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/daily-briefing"
```

## Interpreting Current Candidates

For the recent persisted observation set:

- `SUI/USD` is the strongest early recovery candidate.
- `SOL/USD`, `BTC/USD`, and `ETH/USD` may appear if they repeatedly meet the neutral score band and momentum evidence rules.
- All are EMA 200 blocked.
- All are observe-only.

## Next Phase

Continue collecting persisted observations and review whether early recovery candidates keep improving across multiple market sessions. Any future paper-trade observation should remain separate, explicit, and gated by stronger evidence.

