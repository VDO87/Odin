# SHADOW_RUNTIME_LOOP (ODIN RC1.4)

## 1. O que é o Shadow Runtime Loop
É o ciclo operacional contínuo em modo sombra para manter o ODIN vivo, observável e auditável sem execução real.

## 2. O que o ODIN faz no loop
- Atualiza heartbeat.
- Corre healthchecks periódicos.
- Consulta MT5 Shadow e reconciliação.
- Atualiza snapshot de estado.
- Atualiza contexto do Assistant.
- Corre ciclo ATLAS em `SHADOW_ONLY`.
- Regista eventos e erros estruturados.

## 3. O que o ODIN não faz
- Não envia ordens.
- Não fecha posições.
- Não modifica posições.
- Não ativa trading real.

## 4. Como arrancar
```bash
./run_odin.sh --runtime
```

## 5. Como testar
```bash
./run_odin.sh --runtime-smoke-test
./run_odin.sh --run-once
python -m apps.dashboard_terminal.cli runtime-status
```

## 6. Como ler snapshot
Snapshot principal:
- `data/runtime/odin_state_snapshot.json`

Inclui runtime state, health, mt5, atlas, assistant, llm e flags de segurança.

## 7. Como interpretar eventos
Eventos em:
- `data/runtime/odin_events.jsonl`
- `logs/system/events.log`

Eventos-chave:
- `RUNTIME_STARTED`, `RUNTIME_STOPPED`
- `HEARTBEAT`
- `HEALTHCHECK_*`
- `MT5_STATUS_UPDATED`
- `ATLAS_SHADOW_CYCLE_DONE`
- `ERROR`

## 8. Como pausar/retomar
```bash
python -m apps.dashboard_terminal.cli runtime-pause
python -m apps.dashboard_terminal.cli runtime-resume
```

## 9. Como fazer safe shutdown
```bash
python -m apps.dashboard_terminal.cli runtime-stop
# ou comando runtime safe shutdown via dashboard/command bus
```

## 10. Como preparar soak test
- Confirmar `runtime-status` em `RUNNING`/`DEGRADED` com segurança ativa.
- Confirmar ausência de comandos de execução real.
- Confirmar logs/eventos estáveis por período prolongado.

## 11. Avisos de segurança
- Trading real continua bloqueado.
- MT5 `order_send` continua bloqueado.
- Broker real continua bloqueado.
- LLM/ATLAS sem execução direta.
