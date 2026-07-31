# ODIN supervised DEMO readiness

## Verified locally

- TradeDesk on localhost with replay account, positions, ledger, metrics, decision journal and constrained replay preferences.
- Technical cockpit at `/cockpit`, local logs/SQLite/reports on `D:\ODIN_LOCAL` and Windows desktop launcher.
- Official ECB public observation cached with provenance/hash/freshness; Hermes receives metadata only.
- MT5 terminal detection and persisted DEMO preparation/reconciliation; no terminal contact, access material, login or action path.
- Full validation: 586 tests and 3 subtests passed; runtime smoke passed 21 safe modules.

## Invariants

`safe_to_trade=false`, `real_trading=false` and `execution_allowed=false` remain mandatory. The replay configuration never changes them.

## External activation gate

Supervised DEMO login is not active. It requires a verified DEMO account/server/access material supplied locally in ignored `.env`, followed by an explicit operator authorization for that login. This codebase has no order/action capability, and must not claim it is connected until that authorized check has been completed.
