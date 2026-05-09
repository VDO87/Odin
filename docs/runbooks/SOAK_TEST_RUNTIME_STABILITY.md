# ODIN Soak Test Runtime Stability

## 1) O que é soak test
Soak test é uma execução contínua controlada do runtime em modo sombra para validar estabilidade operacional durante vários ciclos.

## 2) Porque é necessário
Garante que o ODIN se mantém vivo sem crash, sem execução real e com observabilidade confiável antes de testes longos.

## 3) O que valida
- Heartbeat
- Snapshot
- Eventos
- Logs
- Comandos runtime
- Bloqueios de segurança
- Ausência total de ordens

## 4) Como executar
```bash
./run_odin.sh --soak-test-mini
./run_odin.sh --soak-test
python -m apps.dashboard_terminal.cli soak-test --duration-seconds 120
```

## 5) Como interpretar
- `PASS`: estabilidade e segurança confirmadas.
- `WARNING`: funcionamento seguro, mas com degradações/alertas.
- `FAIL`: erro crítico, tentativa de ordem ou invalidação estrutural.

## 6) Critérios antes de PC final
- mini soak passa
- 2h soak passa
- 8h soak passa
- 24h soak recomendado antes de demo assistida prolongada

## 7) O que fazer se houver falhas
- Heartbeat falhar: validar escrita em `data/runtime/odin_heartbeat.json` e permissões.
- Snapshot inválido: validar `data/runtime/odin_state_snapshot.json` e campos de segurança.
- Eventos inválidos: validar JSONL em `data/runtime/odin_events.jsonl`.
- Erro crítico: consultar `logs/errors/soak_test_errors.log` e `logs/errors/runtime_errors.log`.
- Tentativa de ordem detectada: bloquear operação, auditar `logs/system/events.log` e `logs/brokers/requests.log`.

## 8) Segurança obrigatória
- Trading real bloqueado
- `MT5_ORDER_SEND_ENABLED=false`
- `XTB_REAL_ENABLED=false`
- `BROKER_ALLOW_REAL_EXECUTION=false`
- OpenAI OFF por defeito
- LLM e ATLAS sem execução direta
