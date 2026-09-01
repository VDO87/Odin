# ODIN Autonomous DEMO Operations RC2 — Runbook

## Abrir agora

- TradeDesk: `http://127.0.0.1:8765/`
- Cockpit: `http://127.0.0.1:8765/cockpit`
- Relatórios: `D:\ODIN_LOCAL\reports`

## Estado persistente

- Tarefa Windows: `ODIN Autonomous Demo Operations RC2`
- Estado: `D:\ODIN_LOCAL\state\autonomous_demo_state.json`
- Heartbeat: `D:\ODIN_LOCAL\state\autonomous_demo_heartbeat.json`
- Incidentes: `D:\ODIN_LOCAL\state\autonomous_demo_incidents.jsonl`
- Logs: `D:\ODIN_LOCAL\logs\autonomous-demo`
- Hermes triggers: `D:\ODIN_LOCAL\runtime\hermes_analysis_events.jsonl`
- Hermes claims: `D:\ODIN_LOCAL\runtime\hermes_claims.jsonl`
- Resource probe Windows: `get_odin_autonomous_demo_resources.py`, processo
  stdlib isolado com timeout de 45 s; o supervisor acrescenta WSL/FD/memória/
  processos através de um subprobe separado com timeout de 10 s. O Cockpit
  mostra o gate e a telemetria disponível. Temperatura observada >=80 °C pausa
  execução; timeout de qualquer probe também bloqueia.

## Controlos seguros

Os botões TradeDesk são a interface preferida. Em PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\scripts\windows\Set-ODIN-Autonomous-Demo-Control.ps1" -Action PAUSE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\scripts\windows\Set-ODIN-Autonomous-Demo-Control.ps1" -Action SAFE_STOP
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\scripts\windows\Set-ODIN-Autonomous-Demo-Control.ps1" -Action RESUME -ConfirmResume
```

RESUME é apenas um pedido de revalidação. Não transforma nenhuma flag global em
true e não ignora Risk, identidade, freshness, spread, reconciliação ou limites.

## Arranque e paragem do supervisor

```powershell
Start-ScheduledTask -TaskName "ODIN Autonomous Demo Operations RC2"
Stop-ScheduledTask -TaskName "ODIN Autonomous Demo Operations RC2"
```

A tarefa chama diretamente o Python base registado no `pyvenv.cfg` e um
bootstrap Python local, instalado numa pasta imutável identificada pelo
checkpoint em `D:\ODIN_LOCAL\runtime\autonomous-demo`. O bundle contém apenas
`src/odin` e `scripts/windows`, com inventário SHA-256; não copia `.env` nem
credenciais. A configuração canónica continua a ser lida do repositório WSL.
Não existe wrapper CMD/PowerShell no caminho persistente. O Task Scheduler
controla um bootstrap Python mínimo, e este mantém um único supervisor filho
protegido pelo mutex. Se o filho terminar com erro, o bootstrap faz no máximo
três relançamentos bounded após 5 s, 30 s e 60 s; depois termina fail-closed e
regista `SUPERVISOR_RESTART_BUDGET_EXHAUSTED`, sem loop infinito.

Parar a tarefa pausa o supervisor, não fecha posições no broker. Se existir uma
posição DEMO, MT5 continua com SL/TP no broker; na retoma, MT5 é source of truth e
a primeira ação é reconciliação. SAFE STOP no dashboard é preferível durante
operação normal porque mantém observabilidade.

## Pré-requisitos externos

- Terminal exato OANDA TMS aberto e ligado à conta DEMO allowlisted.
- Algo Trading ativado manualmente pelo operador; o ODIN nunca o ativa.
- EURUSD.pro tradable, ticks FRESH e spread <= 0.00030.
- resource gate sem BLOCK; ausência total de telemetria térmica, WSL offline,
  instância lógica duplicada ou temperatura >=80 °C bloqueiam execução.

Mercado fechado, NO_TRADE, spread temporário, stale data, Hermes indisponível ou
reconexão não terminam o supervisor.

## Limites

- EURUSD/EURUSD.pro apenas.
- 0.01 lot.
- 1 posição e 1 ordem em voo.
- 3 trades completos por dia.
- perda realizada diária máxima 5 EUR.
- SL obrigatório; TP/saída determinística.
- REAL e UNKNOWN: HARD BLOCK.

`safe_to_trade=false`  
`real_trading=false`  
`execution_allowed=false`
