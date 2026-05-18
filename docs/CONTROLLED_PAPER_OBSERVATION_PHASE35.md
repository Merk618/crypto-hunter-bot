# Phase 35 Controlled Paper Observation

Phase 35 adds locked infrastructure for controlled paper-trade observation. It is approval-gated, operator-started, paper-only, and disabled by default.

No live trading is added. No real exchange orders are placed.

## Why It Is Disabled By Default

Controlled paper observation can create paper-only trades in a future operator-approved workflow, so the defaults remain conservative:

- `CONTROLLED_PAPER_OBSERVATION_ENABLED=false`
- `CONTROLLED_PAPER_OBSERVATION_ALLOW_BUYS=false`
- `CONTROLLED_PAPER_OBSERVATION_ALLOW_SELLS=false`
- `PAPER_TRADE_OBSERVATION_ENABLED=false`
- `PAPER_TRADE_OBSERVATION_ALLOW_ENABLE=false`

## Required Gates

Controlled paper observation requires:

- approval gate eligibility
- explicit operator start request
- operator acknowledgement
- fresh validation passing
- current risk hygiene clean
- live trading locked
- forbidden live order token absent
- `STRONG_BUY` signal evidence
- risk-approved signal evidence
- configured paper-only buy allowance

## Operator Acknowledgement

Start requests must include:

```json
{
  "manual_start": true,
  "operator_acknowledged": true,
  "allow_paper_trade_preview": true,
  "allow_paper_trade_execution": false
}
```

By default, this can create previews only.

## Preview-Only Mode

Preview mode calculates:

- symbol
- signal score/category
- risk-approved status
- estimated price
- requested notional
- capped notional
- estimated quantity
- fee estimate
- slippage estimate

It creates no paper orders.

## Risk Controls

Defaults:

- max notional per trade: `$25`
- max trades per run: `1`
- max trades per day: `3`
- allowed symbols: `BTC/USD,ETH/USD,SOL/USD,SUI/USD`

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/status"

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/controlled-paper/evaluate" `
  -ContentType "application/json" `
  -Body '{"manual_start":true,"operator_acknowledged":true,"allow_paper_trade_preview":true,"allow_paper_trade_execution":false}'

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/controlled-paper/preview" `
  -ContentType "application/json" `
  -Body '{"manual_start":true,"operator_acknowledged":true,"allow_paper_trade_preview":true,"allow_paper_trade_execution":false}'

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/observation/controlled-paper/run-once" `
  -ContentType "application/json" `
  -Body '{"manual_start":true,"operator_acknowledged":true,"allow_paper_trade_preview":true,"allow_paper_trade_execution":false}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/recent"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-observation"
```

## Live Trading Remains Blocked

Controlled paper observation routes only through the paper broker when explicitly enabled for synthetic paper-only tests. It never calls Kraken live order methods, never calls MooMoo trade APIs, and never creates real broker orders.

## Next Recommendation

Keep collecting observation windows and use preview mode to inspect candidate sizing. A later phase can consider a narrowly scoped operator-controlled paper-only enablement step, but live trading remains out of scope.
