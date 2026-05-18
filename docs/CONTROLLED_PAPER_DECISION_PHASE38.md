# Phase 38 Controlled Paper Preflight Review And Decision

Phase 38 adds a read-only review layer on top of the controlled paper preflight package. It compares preflight, activation plan, controlled paper audit, controlled paper review, fresh validation, risk hygiene, paper-trade readiness, and approval gate status, then returns one operator decision.

This phase does not enable paper trades, does not mutate config, and does not add live trading.

## Preflight Vs Decision

Preflight answers whether the controlled paper activation checks are technically passing.

Decision answers what the operator should do next:

- `BLOCKED`: safety or live-trading guardrails failed.
- `FIX_GUARDRAILS`: controlled paper audit/review or current risk hygiene needs repair.
- `COLLECT_MORE_OBSERVATIONS`: fresh validation or observation count is insufficient.
- `CONTINUE_OBSERVATION_ONLY`: observations exist, but STRONG_BUY or risk-approved evidence is missing.
- `CONFIG_REVIEW_DISABLED`: technical criteria may pass, but config review remains disabled.
- `ELIGIBLE_FOR_CONFIG_REVIEW`: synthetic/full eligibility only; this still does not activate paper trading.

## Why Observe-Only Remains Appropriate

Without repeated `STRONG_BUY` observations and risk-approved observations, Crypto Hunter should stay in observation-only mode. Early recovery candidates remain useful for monitoring, but they are not trade signals and do not bypass EMA 200 or risk filters.

## Config Review Is Separate From Activation

Even when the decision reaches `ELIGIBLE_FOR_CONFIG_REVIEW`, Phase 38 sets:

- `allow_paper_activation=false`
- `allow_live_review=false`
- `paper_trade_execution_allowed_now=false`

Future config review would still require manual operator action in a later phase.

## Endpoints

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/decision"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/decision/checks"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/decision-package"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-decision"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/controlled-paper-next-step"
```

## Safety

Live trading remains blocked. Kraken `AddOrder`, MooMoo order/cancel/unlock methods, withdrawals, transfers, funding, staking, margin trading, and options execution are not implemented.

## Next Recommendation

Continue persisted observation windows until repeated STRONG_BUY and clean risk-approved observations appear. Then review the Phase 38 decision package before considering any future paper-only config review.
