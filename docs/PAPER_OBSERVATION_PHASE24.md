# Paper Observation Mode - Phase 24

Phase 24 adds manual paper observation mode. It monitors Kraken public data, generates Crypto Hunter signals, evaluates risk, records observations, and produces observation reports.

No live trading is added. Paper trades are disabled by default.

## How It Differs From Paper Auto-Trading

Paper auto-trading is designed to scan and optionally place paper buys when all signal and risk rules pass.

Paper observation mode is more conservative:

- It is disabled by default.
- It runs manually with `manual_run=true`.
- It records observations even when risk rejects a trade.
- It does not create paper trades unless `PAPER_OBSERVATION_ALLOW_PAPER_TRADES=true` and the request also allows paper trades.
- It never calls a live broker or exchange order endpoint.

## Config Flags

```text
PAPER_OBSERVATION_ENABLED=false
PAPER_OBSERVATION_READ_ONLY=true
PAPER_OBSERVATION_ALLOW_PAPER_TRADES=false
PAPER_OBSERVATION_SYMBOLS=BTC/USD,ETH/USD,SOL/USD,SUI/USD
PAPER_OBSERVATION_TIMEFRAME=1h
PAPER_OBSERVATION_CANDLE_LIMIT=250
PAPER_OBSERVATION_MIN_SECONDS_BETWEEN_RUNS=300
PAPER_OBSERVATION_MAX_SYMBOLS_PER_RUN=10
PAPER_OBSERVATION_REQUIRE_READINESS=true
PAPER_OBSERVATION_RECORD_ALL_SIGNALS=true
PAPER_OBSERVATION_RECORD_REJECTED_RISK=true
```

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/status"

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/run-once" -ContentType "application/json" -Body '{"manual_run":true,"allow_paper_trades":false}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/recent"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/report"
```

## Report Interpretation

Observation reports summarize:

- signal counts by category
- strongest observed signals
- risk rejections
- paper trades created, if explicitly enabled
- run warnings and blockers
- symbols observed

## Safety

Phase 24 does not add live crypto trading, live stock trading, options execution, Kraken AddOrder, MooMoo order/cancel/unlock methods, withdrawals, transfers, funding, staking, margin trading, or broker execution.

## Next Phase

The next phase can calibrate strategy thresholds from observation history before any larger paper-observation window.
