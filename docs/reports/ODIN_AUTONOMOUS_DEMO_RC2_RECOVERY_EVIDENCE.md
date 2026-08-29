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

### Resource guardian

- Probe real: GPU Quadro M4000 38–39 °C, 23/8192 MB VRAM, WSL ativo, FD soft
  limit 10240, uma instância lógica, RAM e disco acima dos mínimos.
- Temperatura CPU não é exposta por `MSAcpi_ThermalZoneTemperature`; o estado é
  `WARNING=cpu_temperature_telemetry_unavailable`, sem valor inventado.
- Testes offline provam BLOCK a 80 °C, sem telemetria térmica total, WSL offline,
  memória/disco críticos e instância lógica duplicada.

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
