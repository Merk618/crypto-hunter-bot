# Connector Boundaries

Crypto exchange connectors are not the same as brokerage/data connectors.

## Crypto Exchange Connectors

Kraken and Coinbase are crypto exchange connectors.

They use crypto pair symbols such as:

- `BTC/USD`
- `ETH/USD`
- `SOL/USD`

Crypto Hunter owns:

- crypto public market data
- crypto candles
- crypto indicators
- crypto signal scoring
- crypto risk checks
- crypto paper trading
- crypto backtesting
- crypto execution safety gates

## Brokerage/Data Connectors

MooMoo is a brokerage/data connector for stocks, ETFs, and options.

It may eventually support:

- stock quotes
- ETF quotes
- historical candles
- option chains
- watchlists
- scanner data
- stock filtering
- paper/simulated stock and options trading

MooMoo does not belong inside the Crypto Hunter strategy core.

## Do Not Mix Strategy Domains

Do not mix crypto strategy logic with equity/options strategy logic.

Examples:

- `BTC/USD` is a crypto pair.
- `AAPL` is an equity symbol.
- An options contract has expiration, strike, type, multiplier, greeks, and assignment risk.

Each asset class needs its own rules.

## Shared Concepts Later

Shared reporting and risk concepts may be reused later only after clear asset-class boundaries exist.

Possible shared concepts:

- signal result
- risk decision
- paper trade result
- dashboard report
- journal event
- safety audit status

These should be shared as interfaces or reporting schemas, not as one combined strategy engine.

## Boundary Rule

Connect Crypto Hunter and Stock/Options Hunter at the YucaTanaTrades Terminal reporting layer first.

Do not connect them through shared execution code until each asset class has separate safety gates, risk rules, and tests.
