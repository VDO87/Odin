# ODIN DEMO LIVE SOAK RC1 — PRE-FLIGHT

Observed at UTC: `2026-08-23T22:29:12.144397Z`

## Preserved baseline

The branch `feature/demo-live-soak-rc1` starts at `8f4c331`. Its ancestry
contains `9f1df38`, `477c2ce`, `ec18a3a` and `01c481e`. No automatic merge was
performed.

## Read-only pre-flight result

The exact valid terminal is
`C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe`. The installation at
`D:\ODIN_LOCAL\mt5\terminal64.exe` connected to `MetaQuotes-Demo` and is not an
allowed fallback.

The valid OANDA terminal reported:

```text
account=DEMO
broker=OANDA TMS Brokers S.A.
server=OANDATMS-MT5
terminal_connected=true
terminal_trade_allowed=false
account_trade_allowed=true
symbol=EURUSD
normalized_event_time_utc=2026-08-23T22:29:04Z
normalized_data_age_seconds=8.144397
market_time=FRESH
trade_mode=0
bid=1.15583
ask=1.17983
raw_spread=0.02400
point=0.00001
spread_points=2400
symbol_info.spread=2400
spread_limit=0.00030 (30 points)
risk=BLOCK
risk_reason_code=excessive_spread
```

## Decision

The immediate stop conditions `terminal_trade_allowed=false`, market disabled
and excessive spread apply. No Stage 0, `order_check`, CANARY or `order_send`
was run. No retry or autonomous terminal change is allowed. The next pre-flight
requires a later market session and manual terminal authorization by the
operator; it remains subject to all identity, reconciliation, Risk and
idempotency gates.

```text
ODIN DEMO LIVE SOAK RC1 — NOT READY
broker_submission_called=false
safe_to_trade=false
real_trading=false
execution_allowed=false
```
