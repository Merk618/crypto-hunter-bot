# Stock/Options Hunter Phase 16

Phase 16 creates the read-only Stock/Options Hunter skeleton for the YucaTanaTrades ecosystem.

## Purpose

Stock/Options Hunter will eventually use MooMoo as a read-only stock, ETF, and options data source. Phase 16 creates the initial architecture, models, watchlist, scanner, and options-chain analyzer without adding broker execution.

## Difference From Crypto Hunter

Crypto Hunter is for crypto:

- Kraken public crypto market data
- Kraken read-only private account checks
- crypto indicators and signal scoring
- crypto paper trading
- crypto risk management
- future Coinbase crypto adapter

Stock/Options Hunter is for equities, ETFs, and options:

- stock and ETF watchlists
- stock/ETF quote and candle analysis
- options-chain filtering
- liquidity research
- future stock/options paper simulation

The two systems should meet at the YucaTanaTrades Terminal reporting layer, not inside a shared strategy engine.

## MooMoo Dependency

MooMoo remains read-only and optional.

- `MOOMOO_ENABLED=false` by default
- `MOOMOO_READ_ONLY=true`
- `MOOMOO_TRADING_ENABLED=false`
- `MOOMOO_PAPER_TRADING_ENABLED=false`
- `MOOMOO_UNLOCK_TRADE_CONTEXT=false`

If MooMoo or OpenD is unavailable, Stock/Options Hunter returns clean unavailable responses.

## Options Liquidity Filters

Phase 16 filters option research candidates by:

- volume greater than or equal to `STOCK_HUNTER_MIN_OPTION_VOLUME`
- open interest greater than or equal to `STOCK_HUNTER_MIN_OPTION_OPEN_INTEREST`
- bid/ask spread percentage less than or equal to `STOCK_HUNTER_MAX_BID_ASK_SPREAD_PCT`
- call delta between `STOCK_HUNTER_TARGET_DELTA_MIN` and `STOCK_HUNTER_TARGET_DELTA_MAX`
- valid bid and ask values

Default delta target:

- minimum: `0.50`
- maximum: `0.60`

These are research filters only. They are not trade recommendations.

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/watchlist"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/scan"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/analyze/AAPL"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/options/AAPL"
```

## No Trading Yet

Phase 16 does not add:

- live stock trading
- options execution
- MooMoo order placement
- MooMoo trade-context unlock
- margin trading
- funding
- transfers
- withdrawals
- real broker execution

## Future Phases

Potential future phases:

- read-only MooMoo quote/candle adapter
- read-only options-chain adapter
- scanner result persistence
- stock/options dashboard reports
- stock/options paper simulation
- stock/options safety audit
- separate live-trading design only after explicit safety phases
