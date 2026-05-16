# Strategy Calibration Phase 25

Phase 25 adds read-only calibration analysis from paper observation results. It reviews how Crypto Hunter signals behaved during observation runs, highlights repeated blockers, and recommends research-only adjustments without changing thresholds or enabling trading.

## Purpose

The calibration layer answers:

- Are signals consistently too weak?
- Is one blocker, such as the EMA 200 trend filter, dominating results?
- Are NEUTRAL or WEAK signals behaving conservatively in a way that is expected?
- Is there enough observation data to justify future threshold review?

It does not mutate config, strategy code, risk settings, or trading state.

## One Run Is Not Enough

One observation run is useful as a smoke check, not as evidence for threshold changes. If the sample size is below `CALIBRATION_MIN_SAMPLE_SIZE_FOR_CHANGES`, recommendations use `LOW` confidence and tell the operator to collect more observations.

Default:

```env
CALIBRATION_MIN_SAMPLE_SIZE_FOR_CHANGES=20
CALIBRATION_ALLOW_AUTO_APPLY=false
```

## EMA 200 Blocker Dominance

If many observations are blocked because price is at or below EMA 200, the system treats that as conservative trend protection. The calibration report may recommend adding an observation-only early recovery watchlist tag.

It does not recommend removing the EMA 200 requirement for trade consideration.

## Early Recovery Watchlist

An early recovery watchlist would be a future research tag for symbols that show improving momentum while still below EMA 200. It is not a buy signal, not a trade trigger, and not a risk override.

## Observation Calibration vs. Live Trading

Calibration only reads observation results and returns reports. It does not:

- Place real orders
- Place paper trades
- Call Kraken AddOrder
- Unlock MooMoo trading
- Change strategy thresholds
- Lower `MIN_SIGNAL_SCORE_TO_TRADE`
- Modify risk manager rules

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/report"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/symbol/BTC-USD"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/recommendations"
```

## Next Phase

The next recommended phase is a longer paper observation window. Run multiple observation passes across different market conditions, then compare whether the same blockers and score bottlenecks keep repeating.

