# MooMoo Connector Plan

MooMoo is planned as a future stock/options broker and market-data connector. It should not be added directly into the Crypto Hunter trading core.

## Target Architecture

### Crypto Hunter

Crypto Hunter remains focused on crypto markets:

- Kraken crypto market data
- Kraken crypto paper/live-ready safety system
- Coinbase crypto adapter later
- crypto-specific symbols such as `BTC/USD`, `ETH/USD`, and `SOL/USD`
- crypto-specific indicators, signal scoring, risk validation, paper trading, and backtesting

### Stock/Options Hunter

Stock/Options Hunter should be a separate module or service for equities and options:

- MooMoo read-only market data first
- stocks
- ETFs
- options chains
- watchlists
- scanner data
- paper/simulated stock and options trading later
- live stock/options trading locked behind future safety gates

### YucaTanaTrades Terminal

YucaTanaTrades Terminal can later become the dashboard that reads from both systems:

- Crypto Hunter for crypto signals, paper trades, risk, and reports
- Stock/Options Hunter for equities, ETFs, options chains, scanners, and paper trades

The frontend can share presentation patterns without forcing both backends into one strategy engine.

## Future MooMoo Phases

- Phase 16: MooMoo read-only feasibility spike
- Phase 17: Stock/Options Hunter skeleton
- Phase 18: MooMoo market-data adapter
- Phase 19: Options chain scanner
- Phase 20: MooMoo paper/simulated trading only

## Initial Safety Rules For Future MooMoo Work

- Start read-only.
- Do not place stock or options orders in the feasibility phase.
- Do not enable live trading.
- Do not mix crypto and equity symbols in one strategy engine.
- Do not assume crypto risk rules apply to options.
- Do not add account transfer or funding features.
- No withdrawal functionality belongs in this plan.
- Keep all future live stock/options execution behind separate explicit safety gates.

## Why MooMoo Is Separate

Crypto exchanges and stock/options brokers have different data models, trading sessions, order types, settlement behavior, margin rules, option greeks, expiration dates, contract multipliers, and regulatory considerations.

Keeping MooMoo separate avoids making the Crypto Hunter core brittle or ambiguous.
