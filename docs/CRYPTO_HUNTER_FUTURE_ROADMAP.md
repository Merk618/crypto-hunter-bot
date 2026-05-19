# Crypto Hunter Future Roadmap

Crypto Hunter standalone v1 is complete as an observation and safety-first backend. Future work should stay gated and separate.

## Crypto Hunter Future

- Collect longer observation windows.
- Review signal behavior after larger samples.
- Keep early recovery watchlist observe-only.
- Consider controlled paper observation only if all approval gates become eligible.
- Consider tiny live review much later, under a separate approval phase.
- Keep EMA 200 as a trade execution requirement unless manually reviewed.

## Paper Mode Future

Paper mode should remain disabled until:

- Fresh validation passes.
- Current risk hygiene is clean.
- Repeated STRONG_BUY observations exist.
- Repeated risk-approved observations exist.
- Operator approval is explicit.
- Controlled paper guardrails remain clean.

## Live Mode Future

Live mode is not part of v1. Any future live review must be a separate project phase with new audits, manual approvals, tiny limits, and rollback steps.

## SOL Meme Module Future

The Solana meme module should be read-only first and separate from v1 freeze. It should focus on discovery, liquidity checks, rug-risk checks, wallet concentration, and social context before any trading discussion.

## YucaTanaTrades Future

YucaTanaTrades should become a dashboard/control center later. It should connect to Crypto Hunter and the Stock Trader Bot through APIs instead of absorbing bot logic too early.

