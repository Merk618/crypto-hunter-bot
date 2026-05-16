# Observation Window Phase 26

Phase 26 adds a longer paper observation window so Crypto Hunter can collect multiple manual paper-only observation runs over time before any strategy tuning is considered.

## Why Multiple Runs Matter

A single observation run can confirm that Kraken public data, indicators, signals, risk checks, and reporting are working. It is not enough evidence to change strategy thresholds.

Observation windows help answer:

- Are the same blockers repeated across runs?
- Are scores improving or weakening over time?
- Are NEUTRAL or BUY_WATCH candidates appearing repeatedly?
- Is the sample large enough for calibration review?

## How Observation Windows Work

The window manager creates a session and tracks manual runs. It does not start an infinite background loop.

Each `run-next` call delegates to the existing paper observation engine:

- Fetches public Kraken candles
- Generates Crypto Hunter signals
- Evaluates risk
- Records paper-only observation data
- Summarizes window behavior

Paper trades remain disabled by default.

## Config

```env
OBSERVATION_WINDOW_ENABLED=false
OBSERVATION_WINDOW_READ_ONLY=true
OBSERVATION_WINDOW_ALLOW_PAPER_TRADES=false
OBSERVATION_WINDOW_DEFAULT_RUNS=6
OBSERVATION_WINDOW_MIN_RUNS_FOR_SUMMARY=3
OBSERVATION_WINDOW_MINUTES_BETWEEN_RUNS=60
OBSERVATION_WINDOW_MAX_RUNS_PER_DAY=12
OBSERVATION_WINDOW_SYMBOLS=BTC/USD,ETH/USD,SOL/USD,SUI/USD
OBSERVATION_WINDOW_TIMEFRAME=1h
OBSERVATION_WINDOW_CANDLE_LIMIT=250
```

## Endpoint Examples

Start a session:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/start" -ContentType "application/json" -Body '{"target_runs":6,"allow_paper_trades":false}'
```

Run the next manual observation:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/run-next" -ContentType "application/json" -Body '{"manual_run":true,"ignore_interval":true}'
```

Check status and summary:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/window/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/window/summary"
```

Stop or reset:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/stop"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/reset"
```

## Calibration Readiness

- `NOT_READY`: fewer runs than `OBSERVATION_WINDOW_MIN_RUNS_FOR_SUMMARY`
- `PARTIAL`: enough runs for an early summary, but still a small sample
- `READY_FOR_REVIEW`: enough repeated runs to review patterns manually

Readiness never auto-applies changes.

## Safety

Observation windows are paper-only and read-only by default. They do not call Kraken AddOrder, place real exchange orders, unlock MooMoo trading, execute options, or move funds.

## Next Phase

Review observation-window summaries and decide whether strategy tuning is justified. Any future threshold changes should remain manual, tested, and backed by a larger observation sample.

