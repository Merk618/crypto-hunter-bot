# Crypto Hunter Bot

Crypto Hunter is a backend trading engine for a sophisticated crypto trading bot. This repository is intentionally backend-only and is designed to run independently. A separate application may connect to it later through FastAPI.

## Current Phase

Phase 38 controlled paper preflight review and observation decision:

- Clean Python backend project
- FastAPI health and status endpoints
- Pydantic settings
- Paper trading by default
- Live trading safety locks
- Exchange adapter interface
- Kraken public REST market data for AssetPairs, Ticker, OHLC, and Depth
- Coinbase placeholder adapter
- Basic risk and strategy shells
- Indicator engine for candle DataFrames from Phase 2
- Transparent signal scoring and explanation from indicator-enhanced candles
- Safe in-memory paper trading with balances, positions, fees, slippage, realized PnL, and unrealized PnL
- Risk validation, position sizing, cooldown controls, and kill-switch controls
- Manual paper auto-trading scans that combine market data, signals, risk checks, and paper buys
- SQLite trade journal for bot events, signals, risk decisions, paper orders/fills/positions, account snapshots, scan results, and errors
- Offline backtesting engine with trades, equity curve, drawdown, win rate, fees, slippage, and performance metrics
- Read-only reporting API for dashboard overview, paper performance, signal quality, risk status, recent activity, and equity curves
- Kraken private read-only account status and balance connectivity, disabled by default
- Order-intent validation, dry-run execution previews, execution safety gates, and emergency controls
- Centralized dependency wiring for shared runtime services
- Runtime, dependency, and safety-audit system endpoints
- Local smoke-test runner for public Kraken data, indicators, signals, paper bot checks, journal checks, and reporting checks
- Signal calibration report helpers that diagnose strictness without changing thresholds
- Phase 15 local validation checklist and strategy calibration guidance
- MooMoo connector planning as a separate future Stock/Options Hunter module, not part of the Crypto Hunter core
- MooMoo read-only feasibility layer for package/OpenD health and future capability reporting
- Stock/Options Hunter read-only skeleton with watchlist, stock signal placeholder, options-chain analyzer, scanner, and service endpoints
- MooMoo read-only quote, candle, market-state, and option-chain adapter with Stock Hunter integration
- Refined Stock/Options Hunter signal engine with component scoring, RSI/EMA/MACD momentum logic, options liquidity scoring, DTE filters, and scanner ranking
- Dedicated read-only options scanner with best-contract ranking across symbols
- Read-only alert previews, daily briefing summaries, and unified top-candidate reporting across crypto, stocks, and options
- Standalone operator status, startup checks, command summaries, daily briefing scripts, and local runbook endpoints
- Risk hygiene remediation that normalizes future rejected risk decisions and classifies legacy inconsistent records with preview-only tools
- Clean observation verification and legacy-aware readiness that treat legacy risk records as audit warnings while current inconsistencies still block
- Fresh observation-window validation that proves post-remediation observation risk decisions persist cleanly while paper/live trading stay disabled
- Paper-trade approval gate that packages safety, fresh validation, risk hygiene, readiness, and operator review evidence without enabling paper trades
- Controlled paper observation infrastructure with approval gates, preview-only defaults, operator acknowledgement, notional caps, and PaperBroker-only synthetic execution
- Controlled paper review and audit reports that verify disabled defaults, preview-only behavior, paper-only labels, and guardrail status
- Controlled paper activation preflight and read-only activation plan that determine whether future manual config review is reasonable
- Read-only real-data validation helpers, scripts, and local Windows runbook for Kraken public data and optional MooMoo/OpenD checks
- Production-style report filtering, journal hygiene previews, deduped daily briefings, and paper-observation readiness checks
- Manual paper observation mode for Kraken public data, signal generation, risk evaluation, observation logs, and observation reports
- Read-only strategy calibration reports from paper observation results, including EMA 200 blocker analysis, low-score bottleneck detection, and threshold recommendations that cannot auto-apply
- Longer manual paper observation sessions that collect multiple observation runs, summarize repeated blockers, track watchlist candidates, and calculate calibration readiness
- Observation-window accounting fixes, observation-only early recovery classifier, and read-only strategy decision gate for next-step recommendations
- SQLite persistence and hydration for observation runs/results so calibration, decision gates, early recovery, and reports survive backend restarts
- Observation-only Early Recovery Watchlist, report polish, and unified daily briefing section for EMA 200-blocked recovery candidates
- Paper-trade observation readiness gate, risk record hygiene checks, and operator approval structure for a future paper-only phase

Live trading and real exchange order execution are not implemented yet. Crypto Hunter remains standalone-first; YucaTanaTrades frontend integration comes later after local reliability is proven.

## Indicators

Phase 3 calculates:

- EMA 20, EMA 50, EMA 200
- RSI 14
- MACD line, signal, and histogram
- Bollinger Bands 20 with 2 standard deviations
- ATR 14
- OBV, OBV slope 5, and positive OBV trend flag
- ADX 14, plus DI, and minus DI
- Volume SMA 20 and volume-above-SMA flag

## Signal Categories

- `STRONG_BUY`: 80-100
- `BUY_WATCH`: 65-79
- `NEUTRAL`: 50-64
- `WEAK`: 35-49
- `AVOID_SELL`: 0-34

Hard blockers can cap score or category even when raw component scores are high.

## RSI Interpretation

RSI uses period 14. The period is not a buy threshold.

- RSI below 30: oversold with falling-knife risk
- RSI 35-40: early recovery but still weak
- RSI 40-60: ideal bullish momentum zone
- RSI 60-65: strong but slightly extended
- RSI 65-70: elevated; reduce score and avoid chasing
- RSI 70-75: overbought warning and trim/watch metadata
- RSI 75+: hard caution and long-entry score cap

For future exits, RSI 60-70 is not an automatic sell zone. RSI crossing down from above 70, or below 60 after being above 70, is advisory exit metadata only.

## Scoring Breakdown

- Trend: 25 points
- Momentum: 25 points
- Volume/flow: 20 points
- Trend strength: 15 points
- Entry quality: 15 points

Signals include reasons, warnings, blockers, component scores, suggested ATR-based levels, and advisory exit metadata. They do not place or simulate trades.

## Paper Trading

Phase 5 adds manual paper trading only. It simulates trades from explicit market prices supplied by the caller. It does not auto-trade signals and does not send orders to an exchange.

Defaults:

- `PAPER_STARTING_CASH=10000`
- `PAPER_FEE_RATE=0.0025` means 0.25%
- `PAPER_SLIPPAGE_BPS=10` means 10 bps, or 0.10%

Buy fills use `market_price * (1 + slippage_bps / 10000)`.
Sell fills use `market_price * (1 - slippage_bps / 10000)`.

Paper trading is useful for validating mechanics, but it does not guarantee live performance.

## Risk Management

Phase 6 adds a risk decision layer. It does not execute trades. It only approves or rejects proposed trades.

Risk checks include:

- Minimum signal score and `STRONG_BUY` category requirement
- Signal blockers
- Buy/sell side validation
- Market price validation
- Available cash
- Maximum open positions
- Maximum single-position allocation
- Daily realized loss limit
- Spread limit
- Kill switch status
- Symbol cooldowns
- Maximum trades per day
- Consecutive loss limit

## Position Sizing

The risk sizer uses:

```text
risk_amount = equity * MAX_RISK_PER_TRADE
risk_per_unit = abs(entry_price - stop_loss_price)
quantity = risk_amount / risk_per_unit
```

Then quantity is capped by available cash and maximum allocation.

## Kill Switch

The kill switch can be manually activated or triggered after repeated API failures:

- `MAX_API_FAILURES_BEFORE_KILL=5`
- active kill switch rejects all risk evaluations

## Cooldowns

Cooldowns are symbol-specific and timestamp-based:

- `COOLDOWN_AFTER_TRADE_MINUTES=15`
- `COOLDOWN_AFTER_LOSS_MINUTES=60`

Cooldowns only block risk approval. They do not execute or close positions.

## Paper Auto-Trading

Phase 7 adds a manual paper auto-trading loop. It scans configured symbols, generates signals, evaluates risk, and places paper buy orders only when every condition passes.

Defaults:

- `PAPER_AUTO_TRADING_ENABLED=false`
- `PAPER_ALLOW_AUTOBUY=true`
- `PAPER_ALLOW_AUTOSELL=false`
- `BOT_SCAN_TIMEFRAME=1h`
- `BOT_SCAN_LIMIT=250`
- `BOT_MIN_SECONDS_BETWEEN_SCANS=60`

`/bot/start` does not create an infinite blocking loop. Use `/bot/scan-once` to run a manual scan. Auto-selling is disabled by default and no real orders are ever placed.

## SQLite Trade Journal

Phase 8 adds durable SQLite persistence so paper activity can be reviewed after restart.

Defaults:

- `DATABASE_URL=sqlite:///./crypto_hunter.db`
- `ENABLE_TRADE_JOURNAL=true`

Stored records:

- bot events
- signal records
- risk decisions
- paper orders
- paper fills
- paper position snapshots
- account snapshots
- scan results
- error records

API keys and secret-looking payload fields are scrubbed before JSON payloads are stored.

## Backtesting

Phase 9 adds offline backtesting from historical candle DataFrames or JSON candles. It never calls private exchange APIs and never places orders.

Anti-lookahead rule:

- A signal generated on candle `N` can only execute on candle `N+1`.
- The default simulated execution price is the next candle open.

Assumptions:

- Long-only; shorts are disabled by default.
- Entry requires `STRONG_BUY`, minimum score, no hard blockers, and price above EMA 200.
- Exits can occur from stop loss, take profit, bearish MACD, losing EMA 20 after profit, RSI overbought cross-down, or the final candle.
- Buy slippage: `price * (1 + slippage_bps / 10000)`.
- Sell slippage: `price * (1 - slippage_bps / 10000)`.
- Fee: `notional * fee_rate`.

Backtests are research tools. They do not guarantee future performance.

## Reporting API

Phase 10 adds clean JSON reporting endpoints for a future YucaTanaTrades frontend. These endpoints are read-only: they do not start the bot, scan markets, place paper orders, or touch live exchange APIs.

Reports summarize:

- bot state
- paper account performance
- signal category quality
- risk and kill-switch status
- recent journal activity
- account-snapshot equity curve
- full dashboard snapshot

The reporting layer is designed as an API boundary that YucaTanaTrades can later consume without coupling directly to bot internals.

## Kraken Read-Only Account Connection

Phase 11 adds optional Kraken private read-only account connectivity. It can read balances and account status when explicitly enabled, but it cannot place orders, cancel orders, transfer funds, stake, fund, or withdraw.

Defaults:

- `KRAKEN_PRIVATE_READ_ENABLED=false`
- `KRAKEN_PRIVATE_TRADING_ENABLED=false`
- `KRAKEN_REQUIRE_READ_ONLY=true`
- `KRAKEN_ACCOUNT_CACHE_SECONDS=30`

Safe Kraken API key guidance:

- Create a dedicated API key for Crypto Hunter.
- Enable read/query permissions only.
- Do not enable trading.
- Never enable withdrawals.
- Keep funding, staking, transfer, and withdrawal permissions disabled.
- Store keys only in `.env`; they are never returned by the API and are not stored in SQLite.

Example `.env` values:

```text
KRAKEN_API_KEY=your_read_only_key
KRAKEN_API_SECRET=your_read_only_secret
KRAKEN_PRIVATE_READ_ENABLED=true
KRAKEN_PRIVATE_TRADING_ENABLED=false
KRAKEN_REQUIRE_READ_ONLY=true
```

## Execution Safety

Phase 12 prepares the bot for future live execution by validating order intents before any execution layer can touch them. It is dry-run only.

Validation checks include:

- order side and order type
- positive quantity and price
- minimum and maximum notional
- risk approval
- minimum signal score
- `STRONG_BUY` requirement for buy intents
- ticker freshness
- spread/slippage limit
- account balance availability
- optional exchange precision and minimum-size constraints

Defaults:

- `LIVE_TRADING_GATE_ENABLED=false`
- `DRY_RUN_EXECUTION_ENABLED=true`
- `REQUIRE_RISK_APPROVAL_FOR_ORDERS=true`
- `REQUIRE_ACCOUNT_BALANCE_CHECK=true`
- `REQUIRE_SPREAD_CHECK=true`
- `REQUIRE_MARKET_DATA_FRESHNESS=true`
- `MAX_ORDER_NOTIONAL_USD=100`
- `MIN_ORDER_NOTIONAL_USD=5`
- `MAX_ALLOWED_SLIPPAGE_BPS=50`
- `MARKET_DATA_STALE_SECONDS=30`
- `EMERGENCY_CANCEL_ENABLED=false`
- `DEAD_MAN_SWITCH_ENABLED=false`

Dry-run execution returns what would have been sent to an exchange, clearly marked `DRY_RUN`. It does not call Kraken `AddOrder`, cancel live orders, or place any real trade.

Emergency controls can pause or stop the paper bot and can generate a dry-run live-cancel preview. They do not call live exchange endpoints.

## Safety Audit And Runtime Hardening

Phase 13 adds a safety audit and app-state hardening layer before any future live-trading work. It is read-only and does not trigger scans, place trades, or access private Kraken data unless the existing read-only account settings already allow it.

The dependency container keeps stateful services shared consistently:

- one shared `PaperBroker`
- one shared `TradeExecutor`
- one shared `RiskManager`
- one shared `PaperTradingBot`
- one shared `TradeJournal`
- reporting wired to the same paper account state as paper endpoints

The safety audit checks:

- live trading gates remain locked
- default live-trading config is safe
- Kraken private trading remains disabled
- dry-run execution remains enabled
- `ExecutionGuard` cannot execute live orders
- `LiveBroker` refuses orders under default config
- dry-run and validation layers do not depend on a live broker
- forbidden Kraken live-order strings are absent from executable app code
- exchange clients expose no withdrawal, transfer, funding, or staking methods
- secret-like fields are scrubbed before journal serialization
- account endpoints are private-read disabled by default
- bot auto-trading remains paper-only

Before any future live-trading phase, this checklist should be true:

- full test suite passes
- safety audit passes
- dry-run order validation passes
- paper trading has been monitored
- backtests have been reviewed
- Kraken API key permissions are understood
- Kraken keys use read/query permissions until a future live phase explicitly changes that
- no withdrawal permissions are enabled

## Phase 14 Smoke Test And Calibration

Phase 14 adds diagnostics for checking the local backend end-to-end while keeping live trading disabled. The smoke test uses public market data where available, verifies indicators and signals, checks risk evaluation, confirms the paper bot can start manually, records a journal event, and reads the dashboard report. It does not place real orders.

Defaults:

- `PHASE14_SMOKE_SYMBOLS=BTC/USD,ETH/USD,SOL/USD,SUI/USD`
- `PHASE14_TIMEFRAME=1h`
- `PHASE14_CANDLE_LIMIT=250`
- `PHASE14_ALLOW_PAPER_SCAN=false`

Run the local smoke script:

```powershell
cd "C:\Users\brock\Documents\New project 2\crypto-hunter-bot"
.\.venv\Scripts\python.exe scripts\smoke_test_phase14.py
```

Run the API and diagnostics endpoints:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
Invoke-RestMethod -Uri "http://127.0.0.1:8000/diagnostics/smoke-test"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/diagnostics/calibration-report"
```

Calibration status meanings:

- `NORMAL`: signal scoring appears reasonable for the checked market snapshot
- `TOO_STRICT`: synthetic/test bullish conditions cannot reach `BUY_WATCH` or `STRONG_BUY`
- `TOO_LOOSE`: bullish signals appear despite elevated risk context
- `BLOCKED`: signals are limited by explicit blockers
- `DATA_UNAVAILABLE`: candles or signals could not be generated

Phase 14 does not auto-change thresholds. It only reports what it sees.

Next recommended phase: review Phase 14 smoke/calibration output over several market sessions, then add more paper-only monitoring or alerting before considering any future live-trading design.

## Phase 15 MooMoo Read-Only Feasibility

Phase 15 adds documentation for validating Kraken public-data behavior locally and a read-only MooMoo feasibility layer for the broader YucaTanaTrades ecosystem. MooMoo remains separate from the Crypto Hunter core.

Docs:

- [Phase 15 Local Validation](docs/PHASE15_LOCAL_VALIDATION.md)
- [Strategy Calibration Notes](docs/STRATEGY_CALIBRATION.md)
- [MooMoo API And OpenD Setup](docs/MOOMOO_API_SKILLS_SETUP.md)
- [Stock/Options Hunter Plan](docs/STOCK_OPTIONS_HUNTER_PLAN.md)
- [MooMoo Connector Plan](docs/MOOMOO_CONNECTOR_PLAN.md)
- [Connector Boundaries](docs/CONNECTOR_BOUNDARIES.md)

MooMoo is planned as part of a separate future Stock/Options Hunter module. Phase 15 does not install `moomoo-api`, does not require OpenD to be running, and does not unlock trading.

MooMoo defaults:

- `MOOMOO_ENABLED=false`
- `MOOMOO_OPEND_HOST=127.0.0.1`
- `MOOMOO_OPEND_PORT=11111`
- `MOOMOO_READ_ONLY=true`
- `MOOMOO_TRADING_ENABLED=false`
- `MOOMOO_PAPER_TRADING_ENABLED=false`
- `MOOMOO_UNLOCK_TRADE_CONTEXT=false`
- `MOOMOO_MARKET_REGION=US`

Target separation:

- Crypto Hunter: Kraken/Coinbase crypto exchange adapters and crypto strategy/risk systems
- Stock/Options Hunter: future MooMoo read-only market data, stock/ETF/options scanners, and paper simulation
- YucaTanaTrades Terminal: future dashboard that can read from both systems

Phase 15 does not change signal thresholds. Use the calibration notes to review multiple market sessions before making any scoring changes.

MooMoo endpoints:

- `GET /moomoo/status`
- `GET /moomoo/health`
- `GET /moomoo/capabilities`

OpenD setup notes:

- OpenD must be installed separately.
- OpenD must be running and logged in before socket connectivity can pass.
- The default OpenD port is `11111`.
- Python import check after optional local install:

```powershell
.\.venv\Scripts\python.exe -m pip install moomoo-api --upgrade
.\.venv\Scripts\python.exe -c "from moomoo import *; print('MooMoo API import OK')"
```

MooMoo trading remains disabled. Kraken live trading remains disabled.

## Phase 16 Stock/Options Hunter Skeleton

Phase 16 adds a separate read-only Stock/Options Hunter skeleton. It is not part of Crypto Hunter's Kraken execution path.

Docs:

- [Stock/Options Hunter Phase 16](docs/STOCK_OPTIONS_HUNTER_PHASE16.md)
- [Stock/Options Hunter Plan](docs/STOCK_OPTIONS_HUNTER_PLAN.md)
- [Connector Boundaries](docs/CONNECTOR_BOUNDARIES.md)

Defaults:

- `STOCK_HUNTER_ENABLED=false`
- `STOCK_HUNTER_DEFAULT_SYMBOLS=AAPL,MSFT,NVDA,META,AMZN,GOOGL,TSLA`
- `STOCK_HUNTER_ENABLE_OPTIONS_ANALYSIS=true`
- `STOCK_HUNTER_MIN_OPTION_VOLUME=500`
- `STOCK_HUNTER_MIN_OPTION_OPEN_INTEREST=1000`
- `STOCK_HUNTER_MAX_BID_ASK_SPREAD_PCT=8`
- `STOCK_HUNTER_TARGET_DELTA_MIN=0.50`
- `STOCK_HUNTER_TARGET_DELTA_MAX=0.60`
- `STOCK_HUNTER_ALLOW_TRADING=false`
- `STOCK_HUNTER_READ_ONLY=true`

Endpoints:

- `GET /stock-hunter/status`
- `GET /stock-hunter/watchlist`
- `GET /stock-hunter/scan`
- `GET /stock-hunter/analyze/{symbol}`
- `GET /stock-hunter/options/{symbol}`

Phase 16 does not place stock trades, options trades, or real broker orders. MooMoo trading remains disabled. Kraken live trading remains disabled.

## Phase 17 MooMoo Read-Only Market Data

Phase 17 adds a read-only MooMoo market-data adapter for Stock/Options Hunter. It can normalize mocked or future OpenD-backed quotes, candles, market state, and option-chain data.

Docs:

- [MooMoo Market Data Phase 17](docs/MOOMOO_MARKET_DATA_PHASE17.md)

Symbol mapping examples:

- `AAPL` -> `US.AAPL`
- `MSFT` -> `US.MSFT`
- `NVDA` -> `US.NVDA`
- `US.AAPL` remains `US.AAPL`

Crypto symbols such as `BTC/USD` are rejected by the MooMoo mapper.

New endpoints:

- `GET /moomoo/quote/{symbol}`
- `GET /moomoo/candles/{symbol}?timeframe=1d&limit=250`
- `GET /moomoo/options/{symbol}`

If OpenD is disconnected, `moomoo-api` is missing, or `MOOMOO_ENABLED=false`, these endpoints return clean unavailable responses.

MooMoo trading remains disabled. Kraken live trading remains disabled.

## Phase 18 Stock/Options Signal Refinement

Phase 18 refines the read-only Stock/Options Hunter research signals using MooMoo quote, candle, market-state, and option-chain data when available.

Docs:

- [Stock/Options Signal Refinement Phase 18](docs/STOCK_OPTIONS_SIGNAL_REFINEMENT_PHASE18.md)

Refinements:

- Stock score components for trend, momentum, volume/liquidity, market quality, and options support.
- RSI interpretation with elevated and overextended warnings.
- Options DTE filters, liquidity score, contract score, and research-only candidate labels.
- Scanner ranking by `opportunity_score`.

New endpoint:

- `GET /stock-hunter/top-candidates`

MooMoo remains read-only. Options execution is not implemented. Kraken live trading remains disabled.

## Phase 19 Options Scanner

Phase 19 adds a dedicated read-only options scanner and best-contract ranking layer for Stock/Options Hunter.

Docs:

- [Options Scanner Phase 19](docs/OPTIONS_SCANNER_PHASE19.md)

Default filters:

- Volume >= 500
- Open interest >= 1000
- Bid/ask spread <= 8%
- Target delta 0.50 to 0.60
- DTE 14 to 90, preferred 21 to 60

Ranking formula:

- Liquidity score: 30%
- Contract score: 30%
- Underlying stock score: 25%
- DTE quality: 10%
- Spread quality: 5%

Endpoints:

- `GET /options-scanner/status`
- `POST /options-scanner/scan`
- `GET /options-scanner/top`

MooMoo remains read-only. Options execution is not implemented. Kraken live trading remains disabled.

## Phase 20 Alerts and Unified Reporting

Phase 20 adds read-only alert previews and reporting polish for Crypto Hunter, Stock Hunter, and Options Scanner.

Docs:

- [Alerts and Unified Reporting Phase 20](docs/ALERTS_REPORTING_PHASE20.md)

Alert endpoints:

- `GET /alerts/status`
- `GET /alerts/preview`
- `POST /alerts/send-console`
- `POST /alerts/send-discord-dry-run`

Unified report endpoints:

- `GET /reports/unified-summary`
- `GET /reports/top-candidates`
- `GET /reports/daily-briefing`
- `GET /reports/system-health`

Alerts are disabled and read-only by default. Discord is dry-run only in this phase, and webhook URLs are never returned.

## Phase 21 Standalone Operator Polish

Phase 21 keeps Crypto Hunter standalone-first and adds local operator visibility before any future YucaTanaTrades frontend integration.

Docs:

- [Standalone Operator Phase 21](docs/STANDALONE_OPERATOR_PHASE21.md)

Operator endpoints:

- `GET /operator/status`
- `GET /operator/startup-checks`
- `GET /operator/commands`
- `GET /operator/daily-briefing`
- `GET /operator/next-actions`

Operator scripts:

```powershell
.\.venv\Scripts\python.exe scripts\operator_status.py
.\.venv\Scripts\python.exe scripts\operator_smoke_check.py
.\.venv\Scripts\python.exe scripts\operator_daily_briefing.py
```

YucaTanaTrades embedding is intentionally later. This backend should prove reliable as a standalone local bot first.

## Phase 22 Real-Data Validation

Phase 22 adds read-only validation tooling and a Windows runbook for checking the standalone backend against real Kraken public data and optional MooMoo/OpenD read-only data.

Docs:

- [Real-Data Validation Phase 22](docs/REAL_DATA_VALIDATION_PHASE22.md)

Validation endpoints:

- `GET /validation/status`
- `GET /validation/run`
- `GET /validation/kraken`
- `GET /validation/moomoo`
- `GET /validation/report`

Validation scripts:

```powershell
.\.venv\Scripts\python.exe scripts\validate_real_data_phase22.py
.\.venv\Scripts\python.exe scripts\validate_kraken_public.py
.\.venv\Scripts\python.exe scripts\validate_moomoo_readonly.py
```

Unavailable Kraken or MooMoo/OpenD data returns structured warnings or blockers instead of crashing. This remains standalone-first; YucaTanaTrades integration is still later.

## Phase 23 Reporting Hygiene and Observation Readiness

Phase 23 filters fake/test/demo records from production-style reports and adds readiness checks before long-running paper observation mode.

Docs:

- [Reporting Hygiene and Observation Readiness Phase 23](docs/PHASE23_REPORTING_HYGIENE_OBSERVATION_READINESS.md)

Journal hygiene endpoints:

- `GET /journal/hygiene/summary`
- `GET /journal/hygiene/test-records`
- `GET /journal/hygiene/production-preview`

Observation endpoint:

- `GET /observation/readiness`

Daily briefings now exclude fake/test/demo candidates by default, dedupe repeated candidates, and normalize malformed warnings/blockers.

## Phase 24 Paper Observation Mode

Phase 24 adds manual paper observation mode for monitoring Kraken public data over time without live trading.

Docs:

- [Paper Observation Phase 24](docs/PAPER_OBSERVATION_PHASE24.md)

Observation endpoints:

- `GET /observation/status`
- `POST /observation/run-once`
- `GET /observation/recent`
- `GET /observation/report`

Manual run:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/run-once" -ContentType "application/json" -Body '{"manual_run":true,"allow_paper_trades":false}'
```

Paper trades are disabled by default. Even when explicitly enabled later, observation mode can only use the paper broker.

## Phase 25 Strategy Calibration

Phase 25 analyzes paper observation results and recommends calibration review items without changing strategy thresholds.

Docs:

- [Strategy Calibration Phase 25](docs/STRATEGY_CALIBRATION_PHASE25.md)

Calibration endpoints:

- `GET /calibration/status`
- `GET /calibration/report`
- `GET /calibration/symbol/{symbol}`
- `GET /calibration/recommendations`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/report"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/symbol/BTC-USD"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/recommendations"
```

Calibration is read-only. `CALIBRATION_ALLOW_AUTO_APPLY=false` by default, and Phase 25 does not lower `MIN_SIGNAL_SCORE_TO_TRADE`, loosen risk rules, or modify strategy code. The next recommended phase is a longer paper observation window before any manual threshold review.

## Phase 26 Observation Windows

Phase 26 adds longer manual paper observation sessions. A session tracks multiple observation runs over time and summarizes whether signal behavior is consistent enough for later human review.

Docs:

- [Observation Window Phase 26](docs/OBSERVATION_WINDOW_PHASE26.md)

Observation window endpoints:

- `GET /observation/window/status`
- `POST /observation/window/start`
- `POST /observation/window/run-next`
- `POST /observation/window/stop`
- `GET /observation/window/summary`
- `POST /observation/window/reset`

Examples:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/start" -ContentType "application/json" -Body '{"target_runs":6,"allow_paper_trades":false}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/run-next" -ContentType "application/json" -Body '{"manual_run":true,"ignore_interval":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/window/summary"
```

Observation windows do not run an infinite loop inside FastAPI requests. Paper trades remain disabled unless both config and request explicitly allow them, and even then only the paper broker can be used.

## Phase 27 Observation Decision Gate

Phase 27 fixes refused-run accounting and adds a read-only decision gate that can recommend `KEEP_OBSERVING`, `ADD_EARLY_RECOVERY_WATCHLIST`, or future paper-only review states without changing thresholds or enabling trading.

Docs:

- [Observation Decision Gate Phase 27](docs/OBSERVATION_DECISION_GATE_PHASE27.md)

Decision endpoints:

- `GET /observation/decision-gate`
- `GET /observation/early-recovery`
- `GET /calibration/decision-gate`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/decision-gate"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/decision-gate"
```

For the current 20-observation EMA 200-blocked pattern, the intended recommendation is observation-only early recovery tagging. EMA 200 remains required for trade execution, paper-trade observation remains disabled by default, and live review remains blocked.

## Phase 28 Observation Persistence

Phase 28 persists observation runs and results to SQLite, then hydrates them after backend restart for calibration reports, decision gates, early recovery candidates, and observation reports.

Docs:

- [Observation Persistence Phase 28](docs/OBSERVATION_PERSISTENCE_PHASE28.md)

History endpoints:

- `GET /observation/history`
- `GET /observation/history/runs`
- `GET /observation/history/results`
- `GET /observation/history/summary`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history/summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history/runs"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/decision-gate"
```

Completed runs hydrate into reports by default. Refused runs can be included for diagnostics but do not count toward calibration or decision-gate evidence.

## Phase 29 Early Recovery Watchlist

Phase 29 adds a persisted-history powered Early Recovery Watchlist. Candidates are clearly labeled `OBSERVE_ONLY`, `NOT A TRADE SIGNAL`, and `EMA 200 BLOCKED`.

Docs:

- [Early Recovery Watchlist Phase 29](docs/EARLY_RECOVERY_WATCHLIST_PHASE29.md)

Watchlist endpoints:

- `GET /observation/early-recovery/watchlist`
- `GET /observation/early-recovery/report`
- `GET /observation/early-recovery/{symbol}`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/watchlist"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/report"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/SUI-USD"
```

EMA 200 remains required for trade execution. Phase 29 does not enable paper trades, live trades, or threshold auto-apply.

## Phase 30 Paper-Trade Readiness

Phase 30 adds a read-only readiness gate for a future paper-trade observation phase. It checks safety audit status, live-lock status, AddOrder absence, observation sample size, STRONG_BUY evidence, risk approvals, risk record hygiene, and operator approval requirements.

Docs:

- [Paper Trade Readiness Phase 30](docs/PAPER_TRADE_READINESS_PHASE30.md)

Readiness endpoints:

- `GET /observation/paper-trade-readiness`
- `GET /risk/hygiene/summary`
- `GET /risk/hygiene/inconsistencies`
- `GET /risk/readiness`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/readiness"
```

Paper-trade observation remains disabled by default. Early recovery candidates remain observe-only and do not create risk approvals or trades.

## Phase 31 Risk Hygiene Remediation

Phase 31 fixes future risk decision persistence so rejected records cannot carry approval-only quantities or risk amounts. It also adds preview-only classification tools for legacy inconsistent records without deleting or mutating journal history.

Docs:

- [Risk Hygiene Remediation Phase 31](docs/RISK_HYGIENE_REMEDIATION_PHASE31.md)

Risk hygiene endpoints:

- `GET /risk/hygiene/summary`
- `GET /risk/hygiene/inconsistencies`
- `GET /risk/hygiene/classification`
- `GET /risk/hygiene/remediation-preview`
- `GET /risk/hygiene/recent-cleanliness`
- `GET /risk/readiness`
- `GET /observation/paper-trade-readiness`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/classification"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/remediation-preview"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/recent-cleanliness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-readiness"
```

Paper-trade observation remains disabled by default. Legacy inconsistent records are preserved for audit history, and cleanup remains preview-only unless a future phase explicitly adds safe operator-reviewed mutation tools.

## Phase 32 Clean Observation Verification

Phase 32 verifies that new post-remediation observation risk decisions remain clean. It separates current risk inconsistencies from legacy audit records so paper-trade readiness can warn on old journal history without confusing it for current corruption.

Docs:

- [Clean Observation Verification Phase 32](docs/CLEAN_OBSERVATION_VERIFICATION_PHASE32.md)

Verification and readiness endpoints:

- `GET /observation/clean-verification`
- `GET /risk/hygiene/legacy-aware-readiness`
- `GET /risk/hygiene/recent-cleanliness`
- `GET /observation/paper-trade-readiness`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/clean-verification"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/legacy-aware-readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/recent-cleanliness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-readiness"
```

Legacy inconsistent records remain visible for audit history and warn by default. Current inconsistent records still block. Paper-trade observation remains disabled by default and is not enabled in this phase.

## Phase 33 Fresh Observation Validation

Phase 33 validates fresh completed observation windows after the Phase 31/32 risk hygiene fixes. It confirms that new rejected risk decisions classify as clean, current inconsistencies still block, and legacy inconsistent records remain visible as audit warnings.

Docs:

- [Fresh Observation Validation Phase 33](docs/FRESH_OBSERVATION_VALIDATION_PHASE33.md)

Fresh validation endpoints:

- `GET /observation/fresh-validation`
- `GET /observation/fresh-validation/runs`
- `GET /observation/fresh-validation/readiness`
- `GET /operator/fresh-observation-check`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/fresh-validation"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/fresh-validation/runs"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/fresh-validation/readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/fresh-observation-check"
```

Fresh validation can pass without enabling paper trading. Paper-trade observation remains disabled by default, and live trading remains locked.

## Phase 34 Paper-Trade Approval Gate

Phase 34 adds a formal operator review gate for future paper-trade observation. It can identify when the system is blocked, not ready, or eligible for operator review, but it does not approve or enable paper-trade execution.

Docs:

- [Paper Trade Approval Gate Phase 34](docs/PAPER_TRADE_APPROVAL_GATE_PHASE34.md)

Approval endpoints:

- `GET /observation/paper-trade-approval`
- `GET /observation/paper-trade-approval/checks`
- `GET /observation/paper-trade-approval/package`
- `GET /operator/paper-trade-approval-review`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-approval"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-approval/checks"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-approval/package"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/paper-trade-approval-review"
```

Even when the gate returns `ELIGIBLE_FOR_OPERATOR_REVIEW`, `approved_for_paper_trade_observation=false` and `paper_trade_observation_enabled=false` remain enforced in this phase.

## Phase 35 Controlled Paper Observation

Phase 35 adds locked, approval-gated controlled paper observation infrastructure. It is disabled by default and creates previews only unless a future operator-controlled paper-only configuration explicitly enables PaperBroker execution.

Docs:

- [Controlled Paper Observation Phase 35](docs/CONTROLLED_PAPER_OBSERVATION_PHASE35.md)

Controlled paper endpoints:

- `GET /observation/controlled-paper/status`
- `POST /observation/controlled-paper/evaluate`
- `POST /observation/controlled-paper/preview`
- `POST /observation/controlled-paper/run-once`
- `GET /observation/controlled-paper/recent`
- `GET /operator/controlled-paper-observation`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/status"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/controlled-paper/preview" -ContentType "application/json" -Body '{"manual_start":true,"operator_acknowledged":true,"allow_paper_trade_preview":true,"allow_paper_trade_execution":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-observation"
```

Default behavior creates zero paper trades. Live trading and real exchange execution remain unavailable.

## Phase 36 Controlled Paper Review And Audit

Phase 36 adds read-only review and guardrail auditing for controlled paper observation. It verifies disabled defaults, preview-only behavior, zero live trades, zero real execution, and `broker="PAPER"` labels.

Docs:

- [Controlled Paper Review Phase 36](docs/CONTROLLED_PAPER_REVIEW_PHASE36.md)

Review and audit endpoints:

- `GET /observation/controlled-paper/review`
- `GET /observation/controlled-paper/audit`
- `GET /observation/controlled-paper/guardrails`
- `GET /operator/controlled-paper-review`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/review"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/audit"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/guardrails"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-review"
```

Passing guardrails and decision checks means the controlled paper infrastructure is still safe to observe. It does not enable paper trades or live trading.

## Phase 38 Controlled Paper Preflight Review And Decision

Phase 38 adds a read-only operator decision layer on top of the controlled paper preflight package. It reviews preflight, activation plan, controlled paper audit, controlled paper review, fresh validation, risk hygiene, paper-trade readiness, and approval gate outputs, then recommends the safest next action.

Docs:

- [Controlled Paper Decision Phase 38](docs/CONTROLLED_PAPER_DECISION_PHASE38.md)

Decision endpoints:

- `GET /observation/controlled-paper/decision`
- `GET /observation/controlled-paper/decision/checks`
- `GET /observation/controlled-paper/decision-package`
- `GET /operator/controlled-paper-decision`
- `GET /operator/controlled-paper-next-step`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/decision"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/decision-package"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-next-step"
```

Expected conservative output without repeated `STRONG_BUY` and risk-approved observations is `CONTINUE_OBSERVATION_ONLY`. Phase 38 never enables paper activation or live review.

## Phase 37 Controlled Paper Activation Preflight

Phase 37 adds a read-only preflight decision layer for future controlled paper observation activation. It can identify `OBSERVE_ONLY`, `NOT_READY`, `BLOCKED`, or `READY_FOR_OPERATOR_CONFIG_REVIEW` states, but it does not edit config or enable trading.

Docs:

- [Controlled Paper Preflight Phase 37](docs/CONTROLLED_PAPER_PREFLIGHT_PHASE37.md)

Preflight endpoints:

- `GET /observation/controlled-paper/preflight`
- `GET /observation/controlled-paper/preflight/checks`
- `GET /observation/controlled-paper/activation-plan`
- `GET /observation/controlled-paper/preflight-package`
- `GET /operator/controlled-paper-preflight`

Examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/preflight"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/activation-plan"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-preflight"
```

`READY_FOR_OPERATOR_CONFIG_REVIEW` still means paper execution is not enabled. It only means a future manual review could be considered.

## Safety Defaults

The default configuration is intentionally conservative:

- `BOT_MODE=paper`
- `ENABLE_LIVE_TRADING=false`
- `REQUIRE_LIVE_CONFIRMATION=true`
- `LiveBroker` refuses orders unless every live safety condition passes
- `ExecutionGuard` always reports live execution unavailable in Phase 38
- `SafetyAudit` must pass before future execution work
- Exchange API secrets are never returned by API routes
- No withdrawal functionality exists in this repository
- Phase 2/3 use Kraken public endpoints and local indicator calculations only; no API keys are required for indicators

## Setup

```powershell
cd crypto-hunter-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Run Locally

```powershell
uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/status`
- `http://127.0.0.1:8000/market/symbols`
- `http://127.0.0.1:8000/market/ticker/BTC-USD`
- `http://127.0.0.1:8000/market/candles/BTC-USD?timeframe=1h&limit=200`
- `http://127.0.0.1:8000/signals/BTC-USD?timeframe=1h&limit=250`
- `http://127.0.0.1:8000/signals/watchlist?timeframe=1h&limit=250`
- `http://127.0.0.1:8000/paper/account`
- `http://127.0.0.1:8000/paper/positions`
- `http://127.0.0.1:8000/paper/orders`
- `http://127.0.0.1:8000/paper/fills`
- `http://127.0.0.1:8000/risk/status`
- `http://127.0.0.1:8000/bot/status`
- `http://127.0.0.1:8000/journal/events`
- `http://127.0.0.1:8000/journal/signals`
- `http://127.0.0.1:8000/journal/risk-decisions`
- `http://127.0.0.1:8000/journal/orders`
- `http://127.0.0.1:8000/journal/fills`
- `http://127.0.0.1:8000/journal/positions`
- `http://127.0.0.1:8000/journal/account-snapshots`
- `http://127.0.0.1:8000/journal/scans`
- `http://127.0.0.1:8000/journal/errors`
- `http://127.0.0.1:8000/backtest/single`
- `http://127.0.0.1:8000/backtest/watchlist`
- `http://127.0.0.1:8000/reports/overview`
- `http://127.0.0.1:8000/reports/paper-performance`
- `http://127.0.0.1:8000/reports/signal-performance`
- `http://127.0.0.1:8000/reports/risk-summary`
- `http://127.0.0.1:8000/reports/recent-activity`
- `http://127.0.0.1:8000/reports/equity-curve`
- `http://127.0.0.1:8000/reports/full-dashboard`
- `http://127.0.0.1:8000/account/status`
- `http://127.0.0.1:8000/account/balances`
- `http://127.0.0.1:8000/account/summary`
- `http://127.0.0.1:8000/execution/safety-status`
- `http://127.0.0.1:8000/execution/validate-order`
- `http://127.0.0.1:8000/execution/dry-run-order`
- `http://127.0.0.1:8000/execution/dry-runs`
- `http://127.0.0.1:8000/execution/emergency-pause`
- `http://127.0.0.1:8000/execution/emergency-stop`
- `http://127.0.0.1:8000/execution/emergency-cancel-dry-run`
- `http://127.0.0.1:8000/system/runtime`
- `http://127.0.0.1:8000/system/dependencies`
- `http://127.0.0.1:8000/system/safety-audit`
- `http://127.0.0.1:8000/diagnostics/smoke-test`
- `http://127.0.0.1:8000/diagnostics/calibration-report`
- `http://127.0.0.1:8000/moomoo/status`
- `http://127.0.0.1:8000/moomoo/health`
- `http://127.0.0.1:8000/moomoo/capabilities`
- `http://127.0.0.1:8000/moomoo/quote/AAPL`
- `http://127.0.0.1:8000/moomoo/candles/AAPL?timeframe=1d&limit=250`
- `http://127.0.0.1:8000/moomoo/options/AAPL`
- `http://127.0.0.1:8000/stock-hunter/status`
- `http://127.0.0.1:8000/stock-hunter/watchlist`
- `http://127.0.0.1:8000/stock-hunter/scan`
- `http://127.0.0.1:8000/stock-hunter/analyze/AAPL`
- `http://127.0.0.1:8000/stock-hunter/options/AAPL`

Use `BTC-USD` in path parameters because raw `BTC/USD` contains a slash and is not path-safe. The API converts `BTC-USD` to `BTC/USD` internally.

Manual paper buy example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/paper/order" -ContentType "application/json" -Body '{"symbol":"BTC/USD","side":"buy","quantity":0.01,"market_price":65000,"reason":"manual paper test"}'
```

Manual paper close example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/paper/close/BTC-USD" -ContentType "application/json" -Body '{"market_price":66000,"reason":"manual paper close test"}'
```

Risk evaluation example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/risk/evaluate" -ContentType "application/json" -Body '{"symbol":"BTC/USD","side":"buy","market_price":65000,"spread_bps":12,"requested_quantity":null,"signal_result":{"score":84,"category":"STRONG_BUY","blockers":[],"suggested_stop_loss":63000,"suggested_entry":65000}}'
```

Kill switch examples:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/risk/kill-switch/activate" -ContentType "application/json" -Body '{"reason":"manual safety pause"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/risk/kill-switch/deactivate" -ContentType "application/json" -Body '{"reason":"resume testing"}'
```

Manual paper bot scan:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/bot/start" -ContentType "application/json" -Body '{"manual_start":true}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/bot/scan-once"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/bot/stop"
```

Journal initialization and reads:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/journal/init"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/orders?limit=20&symbol=BTC/USD"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/scans?limit=20"
```

Backtest with JSON candles:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/backtest/single" -ContentType "application/json" -Body '{"symbol":"BTC/USD","timeframe":"1h","candles":[{"timestamp":"2026-01-01T00:00:00Z","open":65000,"high":66000,"low":64000,"close":65500,"volume":100}]}'
```

Reporting examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/overview"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/full-dashboard"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/equity-curve?limit=500"
```

Account read-only examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/account/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/account/summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/account/balances"
```

Execution safety examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/execution/safety-status"

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/execution/validate-order" -ContentType "application/json" -Body '{"symbol":"BTC/USD","side":"buy","order_type":"market","quantity":0.001,"estimated_price":65000,"reason":"Phase 12 validation test","signal_score":84,"signal_category":"STRONG_BUY","risk_approved":true}'

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/execution/dry-run-order" -ContentType "application/json" -Body '{"symbol":"BTC/USD","side":"buy","order_type":"market","quantity":0.001,"estimated_price":65000,"reason":"Phase 12 dry-run test","signal_score":84,"signal_category":"STRONG_BUY","risk_approved":true}'

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/execution/emergency-stop" -ContentType "application/json" -Body '{"reason":"manual emergency stop"}'
```

System hardening examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/system/runtime"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/system/dependencies"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/system/safety-audit"
```

Diagnostics examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/diagnostics/smoke-test"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/diagnostics/calibration-report"
```

MooMoo read-only feasibility examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/health"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/capabilities"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/quote/AAPL"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/candles/AAPL?timeframe=1d&limit=250"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/options/AAPL"
```

Stock/Options Hunter read-only examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/watchlist"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/scan"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/top-candidates"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/analyze/AAPL"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/options/AAPL"
```

Phase 18 details:

- [Stock/Options signal refinement](docs/STOCK_OPTIONS_SIGNAL_REFINEMENT_PHASE18.md)
- Stock signals now include trend, momentum, volume/liquidity, market quality, and options-support component scores.
- Options analysis now includes DTE rules, liquidity scores, contract scores, and research-only candidate labels.
- Scanner results are ranked by read-only opportunity score.

Options scanner examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/options-scanner/status"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/options-scanner/scan" -ContentType "application/json" -Body '{"symbols":["AAPL","MSFT","NVDA"],"option_type":"call","top_n":10,"include_rejected":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/options-scanner/top"
```

Alert and unified reporting examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/alerts/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/alerts/preview"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/alerts/send-console"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/alerts/send-discord-dry-run"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/unified-summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/top-candidates"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/daily-briefing"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/system-health"
```

Operator examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/startup-checks"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/commands"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/daily-briefing"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/next-actions"
.\.venv\Scripts\python.exe scripts\operator_status.py
.\.venv\Scripts\python.exe scripts\operator_smoke_check.py
.\.venv\Scripts\python.exe scripts\operator_daily_briefing.py
```

Real-data validation examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/run"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/kraken"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/moomoo"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/validation/report"
.\.venv\Scripts\python.exe scripts\validate_real_data_phase22.py
.\.venv\Scripts\python.exe scripts\validate_kraken_public.py
.\.venv\Scripts\python.exe scripts\validate_moomoo_readonly.py
```

Journal hygiene and observation readiness examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/hygiene/summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/hygiene/test-records"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/journal/hygiene/production-preview"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/readiness"
```

Paper observation examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/status"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/run-once" -ContentType "application/json" -Body '{"manual_run":true,"allow_paper_trades":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/recent"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/report"
```

Calibration examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/report"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/recommendations"
```

Observation window examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/window/status"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/start" -ContentType "application/json" -Body '{"target_runs":6,"allow_paper_trades":false}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/window/run-next" -ContentType "application/json" -Body '{"manual_run":true,"ignore_interval":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/window/summary"
```

Decision gate examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/decision-gate"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/decision-gate"
```

Observation history examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history/results"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/history/summary"
```

Early recovery watchlist examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/watchlist"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/report"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/early-recovery/SUI-USD"
```

Paper-trade readiness examples:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/summary"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/inconsistencies"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/classification"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/remediation-preview"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/recent-cleanliness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/hygiene/legacy-aware-readiness"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/clean-verification"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/fresh-validation"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/fresh-observation-check"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/paper-trade-approval"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/paper-trade-approval-review"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/audit"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/preflight"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/risk/readiness"
```

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Live Trading Warning

Live trading is locked down and not implemented in Phase 38. Kraken private access is read-only account data only. MooMoo is read-only market data only. Stock/Options Hunter, Options Scanner, alerts, unified reports, operator tooling, validation tooling, journal hygiene, risk hygiene, paper-trade readiness, paper-trade approval, controlled paper observation, controlled paper review, controlled paper preflight, controlled paper decision review, observation readiness, paper observation, observation persistence, observation windows, early recovery watchlist, decision gates, and calibration are read-only or paper-only scanner/research/reporting/status/checking modes. Real order placement, live sell execution, live cancel execution, withdrawals, transfers, funding, staking, margin trading, options execution, external alert delivery, and Coinbase integration are not implemented in this phase. Reporting, alerts, operator, validation, journal hygiene, risk hygiene, paper-trade readiness, paper-trade approval, controlled paper observation, controlled paper review, controlled paper preflight, controlled paper decision, observation, observation history, observation window, early recovery, decision gate, calibration, system, diagnostics, MooMoo, Stock/Options Hunter, and Options Scanner endpoints do not perform real exchange execution. Dry-run execution is only a preview, and paper/backtest/smoke-test/scanner/reporting/validation/observation/calibration/decision/watchlist/readiness/approval/controlled-paper/review/preflight results do not guarantee live performance.
