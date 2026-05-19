# Next Project: Stock Trader Bot

The next project should be a separate standalone MooMoo-focused repository, not an embedded module inside Crypto Hunter.

## Initial Scope

- MooMoo read-only feasibility
- Stocks and ETFs scanner
- Options scanner
- Market data normalization
- Paper simulator
- Risk gates
- Operator runbook
- Local health check

## Safety Defaults

- MooMoo trading disabled
- Order placement absent
- Cancel routes absent
- Trade unlock absent
- Options execution absent
- Funding, transfers, withdrawals, staking, and margin absent

## Later Integration

After the Stock Trader Bot proves reliable, YucaTanaTrades can connect to it by API alongside Crypto Hunter.

Do not merge Stock Trader Bot internals into Crypto Hunter.

