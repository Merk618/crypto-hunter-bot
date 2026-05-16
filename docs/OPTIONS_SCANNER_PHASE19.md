# Options Scanner - Phase 19

Phase 19 adds a dedicated read-only options scanner for Stock/Options Hunter. It ranks option contracts for research only and does not place orders, unlock MooMoo trade context, cancel orders, or execute options.

## Purpose

The scanner searches option chains from the read-only MooMoo adapter and ranks contracts using:

- Existing Phase 18 option-chain analysis.
- Underlying stock signal score.
- Liquidity, spread, delta, and DTE quality.

## Filters

Default filters:

- Volume >= 500
- Open interest >= 1000
- Bid/ask spread <= 8%
- Target delta 0.50 to 0.60
- DTE 14 to 90
- Preferred DTE 21 to 60

The defaults are configurable through `OPTIONS_SCANNER_*` environment variables.

## Ranking Formula

`OptionsRankingEngine` combines:

- Liquidity score: 30%
- Contract score: 30%
- Underlying score: 25%
- DTE quality: 10%
- Spread quality: 5%

Contracts are labeled:

- `RESEARCH_CANDIDATE`
- `WATCHLIST_CANDIDATE`
- `REJECTED`

Labels are for research workflow only. They are not execution recommendations.

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/options-scanner/status"

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/options-scanner/scan" -ContentType "application/json" -Body '{"symbols":["AAPL","MSFT","NVDA"],"option_type":"call","top_n":10,"include_rejected":false}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/options-scanner/top"
```

## Safety

MooMoo remains read-only. Stock/Options Hunter trading remains disabled. Options execution is not implemented. Kraken live trading remains locked. No withdrawals, transfers, funding, staking, margin trading, live broker execution, or Kraken AddOrder calls are added in this phase.
