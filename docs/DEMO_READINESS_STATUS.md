# ODIN supervised DEMO readiness

## Verified locally

- TradeDesk on localhost with replay account, positions, ledger, metrics, decision journal and constrained replay preferences.
- Technical cockpit at `/cockpit`, local logs/SQLite/reports on `D:\ODIN_LOCAL` and Windows desktop launcher.
- Official ECB public observation cached with provenance/hash/freshness; Hermes receives metadata only.
- MT5 DEMO read-only collector verified against the local terminal: account summary, open positions, EURUSD quote and 32 M15 candles are persisted locally. Each collection appends a sanitized integrity-hashed event to `D:\ODIN_LOCAL\logs\mt5_demo_readonly.jsonl`.
- Full validation: 586 tests and 3 subtests passed; runtime smoke passed 21 safe modules.

## Invariants

`safe_to_trade=false`, `real_trading=false` and `execution_allowed=false` remain mandatory. The replay configuration never changes them.

## Current DEMO connection scope

The operator authorized and completed a verified DEMO-only terminal login. It is used only by the bounded Windows collector under a 10-second timeout. The collected state is rendered in TradeDesk as observation, separately from replay data. It is not an execution bridge: this codebase has no order/action capability, and `execution_allowed=false` remains mandatory.
