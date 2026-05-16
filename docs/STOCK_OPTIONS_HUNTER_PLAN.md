# Stock/Options Hunter Plan

Stock/Options Hunter is the future home for MooMoo-powered equities, ETFs, and options workflows.

## Separation From Crypto Hunter

Kraken remains Crypto Hunter's crypto market-data and exchange path.

MooMoo should power Stock/Options Hunter, not the Crypto Hunter core.

## Future Scope

Stock/Options Hunter should support:

- stock and ETF quotes
- historical candles
- options chains
- liquidity filters
- watchlists
- scanner data
- paper/simulated trading later

## Future Safety Model

Real trading remains locked until future safety phases.

Initial phases should be:

- read-only package and OpenD feasibility
- read-only market data
- options-chain parsing
- scanner diagnostics
- paper/simulated trading
- separate stock/options risk rules
- separate stock/options execution safety gates

## What Phase 15 Does

Phase 15 only adds:

- MooMoo package import health checks
- optional OpenD socket health checks when enabled
- read-only capability reporting
- documentation for future architecture

Phase 15 does not add:

- stock order placement
- options order placement
- trade-context unlock
- margin trading
- account funding
- transfers
- withdrawals
- Crypto Hunter strategy changes
