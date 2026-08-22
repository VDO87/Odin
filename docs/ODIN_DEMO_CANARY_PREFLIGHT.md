# ODIN DEMO CANARY PRE-FLIGHT

Status: **ODIN DEMO EXECUTION RC1 — WAITING FOR MARKET SESSION**

Evidence captured: `2026-08-22T15:31:18Z`

This is a supervised pre-flight only. No DEMO or REAL order was sent. The
repository control remains disarmed with `canary_authorized=false`.

## Pre-flight

| Check | Observed |
|---|---|
| ACCOUNT | DEMO |
| BROKER | OANDA TMS Brokers S.A. |
| SERVER | OANDATMS-MT5 |
| TERMINAL | `C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe` process verified; `terminal_info.path` is the containing directory |
| TERMINAL CONNECTED | true |
| BALANCE | EUR 50,000.00 DEMO |
| EQUITY | EUR 50,000.00 DEMO |
| SYMBOL | EURUSD |
| SIDE | BUY, technical Stage 0 proposal only |
| VOLUME | 0.01 lot |
| SL | 1.17866 |
| TP | 1.18166 |
| MAX LOSS ESTIMATED | EUR 0.87 DEMO |
| RISK STATUS | BLOCK |
| RISK REASONS | `stale_data`, `stale_data_threshold_exceeded`, `excessive_spread` |
| DATA FRESHNESS | STALE; 59,539 seconds at the final probe |
| RECONCILIATION | RECONCILED |
| TERMINAL TRADE STATE | `live_terminal_trading_not_allowed`; terminal-level permission is external and separate from market session |
| ORDER CHECK | NOT REACHED; blocked correctly before broker validation |
| REAL_TRADING | false |
| SAFE_TO_TRADE | false |
| EXECUTION_ALLOWED | false |
| DEMO_EXECUTION | blocked |
| HUMAN CANARY CONFIRMATION | required after a green Stage 0; not granted |

The requested executable, DEMO account mode, broker, server and configured
login all matched. The local `ODIN_OANDA_SERVER` typo was corrected from the
stale value to the server proved by the already connected DEMO account. No
password or account identifier was printed or persisted in this report.

## Stage 0 evidence

- Runtime: `D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe`
- Raw report: `D:\ODIN_LOCAL\reports\demo-execution\stage0-dry-run.json`
- Raw report SHA-256:
  `8d78a460e59fb3ebe0ee1458e75bb2d3fe0a557b23c97561802c7bd8d1af90ed`
- Result: deterministic fail-closed before `order_check` because the market
  session was closed and market evidence was stale.
- Broker submission called: false.

## External prerequisites pending

### A. MT5 terminal permission

The operator must manually authorize Algo/Auto Trading in the already verified
MT5 DEMO terminal. Before resuming, `terminal_trade_allowed` must be `true`.
ODIN must not change this terminal setting automatically.

### B. EURUSD market session

EURUSD must simultaneously have:

- an open market session;
- `symbol_trade_mode` compatible with trading;
- FRESH ticks within the RC1 freshness limit;
- spread within the documented RC1 limit.

`MARKET_SESSION_REQUIRED` is an accepted external stop condition. Do not run
another dry-run while the market is closed, and do not retry automatically.

## Exact resume command

Run once only after both external prerequisites above are satisfied:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\scripts\windows\Invoke-ODIN-MT5-Demo-DryRun.ps1"
```

Acceptance requires `status=DRY_RUN_VALIDATED`, `risk_status=ALLOW_DEMO`,
`data_freshness=FRESH`, `reconciliation=RECONCILED` and an accepted
`order_check`. Even after that result, the process must stop for a new,
proposal-specific human CANARY confirmation.

The next intended state is:

`CANARY READY — HUMAN CONFIRMATION REQUIRED`

with `broker_submission_called=false`.
