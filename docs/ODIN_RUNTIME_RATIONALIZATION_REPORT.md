# ODIN Runtime Rationalization Report

Data da auditoria: 2026-08-29  
Branch: `feature/autonomous-demo-operations-rc2`  
Âmbito: ODIN Autonomous DEMO Operations RC2

## Resultado

O runtime financeiro ativo fica consolidado numa única cadeia:

`Windows Task Scheduler` → Python base allowlisted → supervisor Python → OANDA
TMS MT5 autorizado. A ação direta elimina o processo filho órfão que o launcher
do venv criava quando a tarefa era parada.

O dashboard permanece num único processo WSL sob watchdog bounded. Risk Engine,
Demo Execution Gate, Data Quality e ledgers continuam módulos determinísticos;
não foram envolvidos por novos agentes ou daemons.

## Inventário e classificação

| Item | Estado | Decisão RC2 |
|---|---|---|
| `ODIN Autonomous Demo Operations RC2` | ACTIVE_REQUIRED | Única tarefa persistente ativa; logon do utilizador, privilégios limitados, `IgnoreNew`, restart bounded. |
| Python base `cpython-3.11.15-windows-x86_64-none\python.exe` | ACTIVE_REQUIRED | Executável direto da tarefa; importa `MetaTrader5 5.0.6070` exclusivamente do venv local já existente. |
| `ODIN RC2 Scheduler Diagnostic` | REMOVE_CANDIDATE | Tarefa de prova já desativada; não participa no runtime. Manter desativada até uma janela de limpeza aprovada. |
| `C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe` | ACTIVE_REQUIRED | Único terminal allowlisted para execução DEMO. |
| `D:\ODIN_LOCAL\mt5\terminal64.exe` | REMOVE_CANDIDATE | MetaQuotes-Demo excluído de launchers, discovery e fallback. Não terminar nem apagar automaticamente. |
| `mt5_autonomous_demo_supervisor.py` | ACTIVE_REQUIRED | Supervisor, heartbeat, reconciliação, bounded recovery, Strategy/Risk/Gate orchestration. Não contém chamada direta a `order_send`. |
| `Get-ODIN-Autonomous-Demo-Resources.ps1` | ACTIVE_REQUIRED | Probe read-only de CPU/RAM/GPU/VRAM/disco/WSL/FD/processos/logs/SQLite/Hermes/Ollama; gate térmico a 80 °C. |
| `Start-ODIN-Dashboard-Persistent.ps1` + `run_dashboard_local.sh` | ACTIVE_REQUIRED | Um dashboard loopback com watchdog bounded. |
| TradeDesk e Cockpit em `127.0.0.1:8765` | ACTIVE_REQUIRED | Duas vistas da mesma aplicação, não dois runtimes. |
| `Set-ODIN-Autonomous-Demo-Control.ps1` e controlos HTTP | ACTIVE_REQUIRED | Um contrato persistente comum para PAUSE, RESUME e SAFE_STOP. |
| Demo Execution Gate + adapter MT5 | ACTIVE_REQUIRED | Fronteira financeira determinística única. |
| Risk Engine | ACTIVE_REQUIRED | Autoridade final de bloqueio; não criar “Agente de Risco” duplicado. |
| Time profile `oanda_tms_mt5_cet_cest_v1` | ACTIVE_REQUIRED | Única normalização ativa para OANDA TMS MT5. |
| Decision Ledger + Execution Ledger | ACTIVE_REQUIRED | Cadeias hash e reconciliação broker-first. |
| Incident memory JSONL | ACTIVE_REQUIRED | Memória durável simples, sem acesso ao broker. |
| Hermes/Ollama local read-only | ACTIVE_OPTIONAL | Indisponibilidade não interrompe mercado, supervisor ou dashboard. |
| Scripts Stage 0, canary one-shot e lifecycle audit RC1 | DEPRECATED | Preservados como evidência/runbook histórico; não são chamados pelo runtime RC2. |
| `Start-ODIN-Autonomous-Demo-RC2.cmd` e launcher PowerShell | DEPRECATED | Preservados para diagnóstico/manual; a tarefa persistente já não os chama. |
| Post-canary soak RC1 | DEPRECATED | Substituído pelo supervisor e métricas RC2 persistentes. |
| Control Center/atalhos Desktop | ACTIVE_OPTIONAL | Interface de operador; não tem autoridade financeira. |
| n8n | DEFERRED | `N8N_DECISION=NOT_NEEDED`; Task Scheduler + supervisor cobrem scheduling, restart e estado. |
| Agent Zero | DEFERRED | Não introduzir durante estabilização DEMO. |
| Oh My Hermes | DEFERRED | Não introduzir nova camada de routing no runtime financeiro. |
| MLflow, OpenTelemetry, Prometheus, Grafana | DEFERRED | Não necessários para a RC2; métricas locais são suficientes. |

## Duplicações observadas

- Existem duas instalações `terminal64.exe`, mas apenas a instalação OANDA TMS
  está autorizada. A MetaQuotes-Demo é uma duplicação operacional excluída, não
  uma fallback.
- Os scripts RC1 de Stage 0/canary continuam no repositório apenas para auditoria.
  A tarefa RC2 não os chama.
- O wrapper CMD e launcher PowerShell RC2 continuam disponíveis, mas foram
  retirados do caminho persistente depois de se provar que o launcher do venv
  deixava processos órfãos fora do Task Scheduler.
- TradeDesk e Cockpit partilham o mesmo servidor local; não existe um segundo
  dashboard daemon.
- O Risk Engine, Demo Gate e Data Quality Gate já satisfazem as capacidades antes
  descritas como “agentes”; não criar wrappers inteligentes duplicados.

## Remoção

Nenhum componente foi apagado nesta auditoria. A remoção futura exige prova de
ausência de referências, checkpoint, desativação prévia e smoke. Relatórios,
ledgers, datasets, canary e branches históricas não são candidatos a remoção.

## Segurança

`safe_to_trade=false`  
`real_trading=false`  
`execution_allowed=false`

REAL e UNKNOWN permanecem HARD BLOCK. Hermes, n8n, Strategy e LLM não têm acesso
direto a `mt5.order_send`.
