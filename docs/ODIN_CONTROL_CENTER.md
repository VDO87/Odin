# ODIN Control Center

Status: local Windows access surface. It does not move canonical files, copy
logs, authorize CANARY, or provide financial execution authority.

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

## Location and reconstruction

The generated directory is:

```text
C:\Users\ODIN\Desktop\ODIN - CONTROL CENTER
```

Rebuild or update it from a normal, non-administrator PowerShell session:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\scripts\windows\Install-ODIN-Control-Center.ps1"
```

Validate the installed shortcut metadata without launching commands:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\scripts\windows\Install-ODIN-Control-Center.ps1" -ValidateOnly
```

The installer creates only directories, Windows `.lnk` files, and the generated
`ODIN - ESTADO ATUAL.txt`. Every data/log/report shortcut continues to point at
the real canonical location.

## Structure

| Folder | Purpose |
|---|---|
| `01 - OPERACAO` | TradeDesk, technical cockpit, exact OANDA DEMO MT5 installation, Hermes and a read-only health check. |
| `02 - DEMO TRADING` | Stage 0 dry-run launcher, CANARY pre-flight documentation and existing DEMO/MT5 report locations. |
| `03 - SUPERVISAO` | One-shot Daily Supervisor and Weekly Evolution Gate plus current reports. |
| `04 - LOGS` | Existing ODIN, cockpit, MT5 and Hermes logs; audit docs; Decision Ledger and SQLite diagnostic file selectors. |
| `05 - DESENVOLVIMENTO` | VS Code/WSL/repository/docs access and read-only Git status. |
| `06 - SISTEMA` | Task Scheduler, NVIDIA monitor, ODIN process status, installed Ollama, Task Manager and Resource Monitor. |
| `99 - EMERGENCIA` | Safe-stop and recovery documentation, read-only kill-switch status and checkpoints. |

## Canonical endpoints and paths

- TradeDesk: `http://127.0.0.1:8765/`
- Technical cockpit: `http://127.0.0.1:8765/cockpit`
- Repository: `/home/odin/projects/odin`
- Windows repository view: `\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin`
- Reports: `D:\ODIN_LOCAL\reports`
- ODIN logs: `D:\ODIN_LOCAL\logs`
- Runtime evidence, ledger and SQLite: `D:\ODIN_LOCAL\runtime`
- OANDA DEMO terminal: `C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe`

MT5 log locations are resolved at installation time from each terminal data
directory's `origin.txt`. A shortcut is created only when that origin and its
real `logs` directory both exist. The same existence rule applies to optional
components and latest reports.

## Shortcut safety and authority

TradeDesk and cockpit call the existing local launcher and then open their
confirmed localhost endpoints. Health, Git, kill-switch, logs, reports,
ledger, SQLite and system-monitoring shortcuts are read-only. Daily Supervisor
and Weekly Evolution Gate write new evidence reports only; neither starts an
initiative or changes the running system.

`Stage 0 DEMO Dry Run` reuses
`scripts/windows/Invoke-ODIN-MT5-Demo-DryRun.ps1`. It does not grant the human
CANARY confirmation and does not call `mt5.order_send`. It must only be run by
the operator under the RC1 preconditions documented in
`docs/ODIN_DEMO_CANARY_PREFLIGHT.md`.

There is deliberately no one-click command to close positions, send orders,
alter the MT5 Algo/Auto Trading setting, kill arbitrary processes, delete
state, restore checkpoints or close MT5. The emergency folder contains
read-only status and documentation. Any potentially destructive recovery or
future CANARY action continues to require explicit human confirmation.

## Status refresh

The root shortcut `Refresh ODIN Status` invokes
`scripts/windows/Refresh-ODIN-Control-Center-Status.ps1`. It rewrites only the
generated status text from local evidence: timestamp, branch, HEAD, worktree,
RC1 mode/status, three guardrails, non-sensitive MT5 identity, localhost
availability, canonical paths and latest daily/weekly reports. Account login,
passwords, tokens and API keys are never read into the output.

## Validation boundary

Installer validation resolves every `.lnk`, verifies that its target and
working directory exist, and rejects shortcut command surfaces containing
`order_send` or a true CANARY authorization. It does not execute Stage 0,
CANARY, supervisor commands, MT5, or any financial action. Safe live smoke is
limited to the localhost health probes and status generation.
