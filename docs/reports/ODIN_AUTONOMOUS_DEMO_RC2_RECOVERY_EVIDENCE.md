# ODIN Autonomous DEMO RC2 — Recovery Evidence

Data: 2026-08-29  
Branch: `feature/autonomous-demo-operations-rc2`

## Provas executadas

### Single instance

- A tarefa `ODIN Autonomous Demo Operations RC2` foi iniciada enquanto já estava
  `Running`.
- PID antes: `18968`.
- PID depois: `18968`.
- Resultado: `PASS`; `IgnoreNew` + mutex impediram uma segunda instância lógica.

### Restart do supervisor

- Tarefa parada e cadeia RC2 exata terminada apenas com zero posições e zero
  ordens comprovadas.
- Tarefa reinstalada sem password, privilégios limitados e iniciada novamente.
- Heartbeat retomou e passou a publicar cada novo checkpoint.
- Estado final: `WAITING_MARKET`; `broker_submission_called=false`.
- Resultado: `PASS`.

### Controlo real pelo Task Scheduler

- O caminho antigo via Python do venv deixava dois processos pai/filho vivos
  depois de `Stop-ScheduledTask`; o teste foi classificado como falha real.
- A tarefa passou a executar diretamente o Python base indicado no
  `pyvenv.cfg`, mantendo o `site-packages` MT5 local sem instalação nem PATH.
- Após a correção: estado da tarefa `Ready`, processos RC2 após stop `0`;
  depois do start, tarefa `Running`, processos RC2 `1`, checkpoint `bf14f19`.
- Resultado: `PASS`; o scheduler controla agora o processo real.

### Restart do TradeDesk/Cockpit

- O processo WSL do dashboard foi terminado de forma controlada.
- `Start-ODIN-Dashboard-Persistent.ps1` iniciou uma nova instância.
- `http://127.0.0.1:8765/health` voltou a HTTP 200.
- A rota `/operations/autonomous-demo` expôs métricas e Hermes-versus-Reality.
- Resultado: `PASS`.
- Revalidação no checkpoint `cf5112c`: o listener anterior foi terminado e o
  watchdog recuperou `127.0.0.1:8765` com novo PID, ambas as páginas HTTP 200,
  resource gate e painéis RISK/EXECUTION visíveis.
- Revalidação no checkpoint `06d4023`: o listener foi terminado apenas com
  `SIGTERM` e recuperado pelo launcher bounded. Health, TradeDesk e Cockpit
  voltaram a HTTP 200; o TradeDesk expôs o cartão `Analysis` e a rota
  `/operations/autonomous-demo` publicou `ANALYZED/SCORED`, sem posições,
  ordens ou submissão ao broker.

### Resource guardian

- Probe real: GPU Quadro M4000 38–39 °C, 23/8192 MB VRAM, WSL ativo, FD soft
  limit 10240, uma instância lógica, RAM e disco acima dos mínimos.
- Temperatura CPU não é exposta por `MSAcpi_ThermalZoneTemperature`; o estado é
  `WARNING=cpu_temperature_telemetry_unavailable`, sem valor inventado.
- Testes offline provam BLOCK a 80 °C, sem telemetria térmica total, WSL offline,
  memória/disco críticos e instância lógica duplicada.
- A falha intermitente `resource_probe_unavailable` foi reproduzida com o probe
  PowerShell a bloquear em chamadas WSL aninhadas. A correção separou o probe
  Windows do subprobe WSL, que passou a ter processo e timeout próprios de 10 s.
- Cinco ciclos reais consecutivos observaram WSL em 234--625 ms, uma instância
  lógica, zero exposição e gate sem BLOCK. Um timeout futuro do subprobe continua
  fail-closed com reason code específico.

### Integridade do incident ledger

- Durante uma limpeza de namespace Windows/WSL, o ficheiro JSONL de incidentes
  foi acidentalmente truncado. A ocorrência foi registada explicitamente como
  `INCIDENT_LEDGER_ACCIDENTAL_RESET`; não foi ocultada.
- A linha que existia depois do reset foi preservada em
  `D:\ODIN_LOCAL\reports\recovery\autonomous_demo_incidents_after_accidental_reset_20260829T143916Z.jsonl`
  com SHA-256
  `6b49075f15994b22bcfcc6e657145d435c869adf559dd30ee9a471031af679c6`.
- O ledger foi reconstruído a partir da saída JSONL exata anteriormente
  observada e da semântica determinística de append. Os registos recuperados
  têm marcadores `recovered_after_accidental_reset=true` e `recovery_basis`;
  o supervisor continuou depois a acrescentar incidentes normalmente.

### Hermes-versus-Reality

- O adapter local bounded processa no máximo um trigger novo por ciclo e não tem
  autoridade sobre Strategy, Risk ou execução.
- O primeiro trigger do canary terminou em `MODEL_TIMEOUT` e não foi repetido.
  Saídas truncadas ou placeholders de schema passaram a ser rejeitadas.
- A última prova real no checkpoint `06d4023` produziu uma claim factual para
  `nested_wsl_probe_blocked_parent`, classificada `CONFIRMED`, em 2,344 s.
- As quatro claims anteriores classificadas `CONTRADICTED/HALLUCINATION` foram
  preservadas como evidência; não foram apagadas para melhorar métricas.

### Regressão pré-soak

- Matriz direcionada RC2: `206 passed, 3 subtests passed`.
- Suite completa sem exclusões: `852 passed, 42 subtests passed` em 595,12 s,
  com file descriptor soft limit 8192.
- Ruff global: PASS. Mypy dirigido: PASS em seis módulos fonte alterados.
- Parse PowerShell: PASS nos três scripts RC2 alterados. `git diff --check`: PASS.
- Este resultado é validação pré-soak; a suite final continua a ter de ser
  repetida depois dos gates operacionais de 24 h e cinco trades.

### Supervisor visível no TradeDesk

- O checkpoint `7fa5ccd` tornou explícitos na Visão Geral: uptime, ciclo,
  próximo check, branch, checkpoint e último repair.
- Validação no browser local confirmou os seis campos com dados vivos, além de
  `SUPERVISOR RUNNING`, `MARKET CLOSED / WAITING`, `MT5 CONNECTED`,
  `HERMES AVAILABLE` e zero erros de consola.
- A alteração é exclusivamente read-only e de apresentação; não adiciona
  endpoints de controlo nem capacidade financeira.

### Restart do WSL

- Pré-condições: zero posições, zero ordens, mercado stale e nenhuma submissão.
- `Ubuntu-ODIN` foi terminado de forma controlada.
- O supervisor Windows manteve o mesmo PID `18968`.
- Heartbeat avançou de `2026-08-29T12:33:23.694781Z` para
  `2026-08-29T12:33:58.564723Z`.
- O watchdog reergueu WSL e o dashboard voltou a HTTP 200.
- Estado final: `WAITING_MARKET`, checkpoint `ae5be45` e
  `broker_submission_called=false`.
- Resultado: `PASS`.

## Testes não forçados

- Restart Windows: não executado nesta sessão para não interromper o operador;
  autoarranque está instalado no Task Scheduler e permanece por validar após um
  reboot humano oportuno.
- Restart com posição aberta: não executado porque não existe posição e é proibido
  forçar um trade para criar evidência. O recovery path broker-first tem testes
  offline e será observado quando surgir uma posição legítima.
- Resposta perdida de broker: coberta por testes fake/offline; não provocar timeout
  real nem reenviar ordem.

`safe_to_trade=false`  
`real_trading=false`  
`execution_allowed=false`
