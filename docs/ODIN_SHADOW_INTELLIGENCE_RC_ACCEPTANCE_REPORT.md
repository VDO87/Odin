# ODIN SHADOW INTELLIGENCE RC — Acceptance Report

**Date:** 2026-08-15  
**Baseline parent:** `9f1df38` (`ODIN DEMO BASELINE — READY FOR SUPERVISED TESTING`)  
**Dedicated branch:** `feature/shadow-intelligence-rc1`  
**RC implementation checkpoints:** `e64249a`, `7448db5`, `877e92b`, `76842f0`,
`cacf25b`, `fe71b3a`

## Decision

**ODIN SHADOW INTELLIGENCE RC — READY FOR SUPERVISED SOAK TEST**

This decision authorises only supervised local observation and deterministic
replay. It never authorises a financial action.

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

## Immutable baseline and soak

- The RC branch was created from `9f1df38`; Git confirms that baseline commit
  is an ancestor and no merge was performed.
- [ODIN_BASELINE_SOAK_REPORT.md](ODIN_BASELINE_SOAK_REPORT.md) records the
  bounded supervised refresh: MT5 `CONNECTED_DEMO_READ_ONLY`, ECB provenance,
  Hermes `LOCAL_ONLY`, no crash, Quadro M4000 at 40°C and guardrails false.

## Delivered contracts and pipeline

| Requirement | Evidence |
|---|---|
| Provider-neutral Market Data | `MarketBar`; MT5 read-only, P0 canonical and local replay normalize before strategy. |
| Deterministic MarketState | `MarketState` calculates freshness, quality, trend, volatility, spread proxy, session, availability, reconciliation and input hash. |
| Shadow strategy | Transparent five-bar trend baseline emits only `BUY`, `SELL`, `HOLD` or `BLOCKED`; it has no broker interface. |
| Risk Engine | Deterministic `ALLOW_SHADOW`, `RESTRICT`, `BLOCK`, `KILL`; covers stale/bad/missing data, excessive spread, reconciliation, drawdown and kill switch. |
| Decision Ledger | Local append-only JSONL includes decision, Git commit and record hash; live sanitized-MT5 trial produced a `BLOCKED` stale-data decision with execution false. |
| Replay | Same pipeline uses accepted P0 M15; two full runs over 2,147 bars / 2,142 decisions produced the same hash in 1.395 s, with `lookahead=false`. |
| Hermes context | `ContextPacket` is evidence-only and cannot alter MarketState or RiskResult. |
| Visual separation | TradeDesk and cockpit label `SHADOW INTELLIGENCE · REPLAY ONLY` and expose no execution control. |

## Dataset provenance

The replay consumed P0 dataset
`50e422310881add19674b390f06497070a61b2b1bc6470f77de57a9bca96c217`:
EURUSD M15 derived deterministically from OANDA TMS/MT5 M1 RAW. Provenance,
gap quality and `license_id=NOT_EXPLICITLY_STATED` remain in its validated
manifest. No rights of redistribution are inferred.

## Validation

| Check | Result |
|---|---|
| Shadow-specific tests | 10 passed |
| Shadow/TradeDesk/cockpit/replay regression | 13 passed |
| Full suite | 633 passed, 42 subtests passed, 0 failed/skipped |
| Full-suite duration | 431.48 s (7m11s), FD limit 8,192 |
| Ruff | `ruff check .` passed |
| Mypy | Shadow RC scope: 8 source files, passed |
| Git whitespace | `git diff --check` passed |
| Real dashboard endpoint | `/shadow/intelligence` HTTP 200, `SHADOW_REPLAY`, all three guardrails false |

## Residual boundaries

- No `order_send`, broker action, DEMO order, real order, deposit or credential
  change was introduced.
- MT5 live/read-only input is intentionally blocked when stale; the recorded
  stale-data decision is evidence that fail-closed risk works.
- No persistent daemon, merge, force push, Shadow Intelligence expansion or
  financial-agent authority was created.

## Supervised soak procedure

Use the existing bounded refresh to update the sanitized MT5/public evidence,
then inspect `/shadow/intelligence`, the cockpit and the local ledger. A stale,
missing or degraded source must remain `BLOCKED`; it must never be repaired by
synthetic bars, forward-fill or execution.
