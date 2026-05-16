# MooMoo Market Data Phase 17

Phase 17 adds a read-only MooMoo market-data adapter for Stock/Options Hunter.

## Requirements For Real Local Data

Real MooMoo data requires:

- OpenD installed
- OpenD running
- OpenD logged in
- `moomoo-api` installed in the Python environment
- `MOOMOO_ENABLED=true`
- `MOOMOO_READ_ONLY=true`
- `MOOMOO_TRADING_ENABLED=false`
- `MOOMOO_UNLOCK_TRADE_CONTEXT=false`

If OpenD is disconnected or the package is unavailable, the adapter returns clean unavailable responses.

## Symbol Mapping

Common stock symbols are mapped to MooMoo provider symbols:

- `AAPL` -> `US.AAPL`
- `MSFT` -> `US.MSFT`
- `NVDA` -> `US.NVDA`
- `META` -> `US.META`
- `TSLA` -> `US.TSLA`

Already-prefixed symbols such as `US.AAPL` are preserved.

Crypto symbols are rejected:

- `BTC/USD`
- `ETH/USD`
- `SOL/USD`
- `XRP/USD`

Crypto symbols belong in Crypto Hunter, not Stock/Options Hunter.

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/quote/AAPL"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/candles/AAPL?timeframe=1d&limit=250"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/options/AAPL"
```

Stock Hunter endpoints use the same read-only adapter when MooMoo is available:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/analyze/AAPL"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/options/AAPL"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/scan"
```

## Supported Timeframes

- `1m`
- `5m`
- `15m`
- `30m`
- `1h`
- `1d`
- `1w`

## Disconnected Behavior

When MooMoo is disabled, OpenD is disconnected, or `moomoo-api` is missing:

- quote responses return `available=false`
- candle responses return an empty `candles` list
- option responses return an empty `contracts` list
- Stock Hunter results become `DATA_UNAVAILABLE` or `NO_ACTION`
- no exception should crash the app

## No Trading

Phase 17 does not add:

- live stock trading
- options execution
- MooMoo order placement
- order cancellation
- trade-context unlock
- margin trading
- funding
- transfers
- withdrawals
- real broker execution
