# ODIN Trader Console Testing

## Objetivo
Validar localmente a ligação operacional entre Browser Dashboard, API da consola, CommandGateway e CoreRuntimeController.

## Pré-requisitos
- instalação Odin preparada (recomendado: `$HOME/odin-runtime`);
- `config/odin.local.toml` válido na pasta de instalação;
- portas locais livres (`8080` para consola).

Importante neste corte:
- não correr `start_odin.sh` e `apps.operator_console` ao mesmo tempo;
- ambos arrancam um runtime local e partilhar `runtime/state/core_state.db` em paralelo pode criar estado de recovery inconsistente.

## A. Terminal 1 (CORE daemon, opcional)
```bash
$HOME/odin-runtime/bin/start_odin.sh
```

Resultado esperado:
- processo fica ativo;
- ficheiro `"$HOME/odin-runtime/runtime/state/core_public_view.json"` é atualizado.

Se falhar:
- validar `config/odin.local.toml`;
- validar `.venv` e permissões da pasta `runtime/`.

## B. Terminal 2 (Operator Console, recomendado para testes UI/API)
```bash
$HOME/odin-runtime/bin/start_operator_console.sh
```

Resultado esperado:
- saída com URL da consola;
- API HTTP em `127.0.0.1:8080`.
- runtime local próprio da consola ativo.

Se falhar:
- confirmar que a porta `8080` está livre;
- confirmar dependências da `.venv`.

Para testes da consola, usar apenas este processo.

## C. Browser
Abrir:
```text
http://127.0.0.1:8080
```

Resultado esperado:
- `Dashboard` mostra resumo do estado;
- `Market Data` mostra providers/cache/calendar e botão de inject;
- `Market` mostra runtime MARKET;
- `Commands` mostra resultado de comandos;
- `Config` mostra configuração ativa;
- `Integrations`/`Intelligence` mantêm placeholders.

## D. Testes por curl
```bash
curl http://127.0.0.1:8080/api/status | python3 -m json.tool
curl http://127.0.0.1:8080/api/health | python3 -m json.tool
curl http://127.0.0.1:8080/api/config | python3 -m json.tool
curl http://127.0.0.1:8080/api/external/status | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/external/inject-demo-quote-to-market | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle \
  -H "Content-Type: application/json" \
  -d '{"requested_by":"operator-cli","role":"operator"}' \
  | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle \
  -H "Content-Type: application/json" \
  -d '{"mode":"test","requested_by":"operator-cli","role":"operator"}' \
  | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle \
  -H "Content-Type: application/json" \
  -d '{"mode":"test","force_risk_block":true,"requested_by":"operator-cli","role":"operator"}' \
  | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/commands/pause \
  -H "Content-Type: application/json" \
  -d '{"confirmation":true,"requested_by":"operator-cli","role":"operator","authorization_context":{"ticket":"ops-pause-1"}}' \
  | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/commands/resume \
  -H "Content-Type: application/json" \
  -d '{"confirmation":true,"requested_by":"operator-cli","role":"operator","authorization_context":{"ticket":"ops-resume-1"}}' \
  | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/commands/stop \
  -H "Content-Type: application/json" \
  -d '{"confirmation":true,"requested_by":"operator-cli","role":"operator","authorization_context":{"ticket":"ops-stop-1"}}' \
  | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/logs/export | python3 -m json.tool
```

### Interpretação rápida por endpoint
1. `/api/status`
- esperado: `global_state`, `mode`, `profile`, `readiness`, `integrity`, `kill_active`, `active_block_count`, `liveness`.
- falha típica: payload incompleto ou `status_file_present=false` quando o daemon devia estar a escrever.
- verificar: `"$HOME/odin-runtime/runtime/state/core_public_view.json"`.

2. `/api/health`
- esperado: `liveness`, `startup_required_modules`, `startup_missing_heartbeat_modules`, `startup_unavailable_modules`, contadores `critical_module_*`.
- falha típica: liveness vazio ou contadores ausentes.
- verificar: arranque do CORE no Terminal 1.

3. `/api/config`
- esperado: profile ativo, modo de execução e configuração carregada sem erro fatal.
- falha típica: ficheiro local inválido ou missing fields obrigatórios.
- verificar: `"$HOME/odin-runtime/config/odin.local.toml"` e output de `apps.validate_config`.

4. `/api/external/status`
- esperado: providers, cache, warnings.
- em `lite`: warning de provider real desativado é normal.
- falha típica: erro 500; verificar logs externos.

5. `POST /api/external/inject-demo-quote-to-market`
- esperado: `accepted/rejected`, `gate_status`, `instrument_id`, `feed_id`, `reason_code`.
- se `accepted=true`: `Market` page deve refletir `last_instrument_id=EURUSD`, `last_feed_id=primary`.
- debug esperado no payload: `injected_quote_timestamp`, `ingested_at_utc`, `sample_age_ms`, `max_valid_age_ms`, `market_assessment_state`, `decision_market_ready`.
- falha típica: `gate_status=rejected`; inspecionar `reason_code`.

6. `POST /api/commands/pause` e `POST /api/commands/resume`
- sem `confirmation=true`: devolve rejeição com `reason_code=confirmation_required`.
- runtime offline: deve devolver `runtime_not_active`.
- falha típica: comando rejeitado por estado/autorização.

Exemplo de rejeição (sem confirmação):
```json
{
  "accepted": false,
  "command": "pause",
  "reason_code": "confirmation_required",
  "rejection_reason": "confirmation_required",
  "confirmation_required": true
}
```

Exemplo de aceite (com confirmação):
```json
{
  "accepted": true,
  "command": "pause",
  "reason_code": null,
  "rejection_reason": null,
  "confirmation_required": false
}
```

Nota:
- campo de confirmação aceite pela API: `confirmation` (boolean) no body JSON.
- `pause`, `resume` e `stop` seguem o mesmo formato.

7. `POST /api/test/run-decision-cycle`
- `mode`:
  - `safe` (default): devolve `NO_ACTION`.
  - `test`: pode emitir `CANDIDATE_SELECTED` e gerar `ExecutionIntent` demo.
- campo canónico atual para override: `mode` (não `decision_mode`).
- `force_risk_block=true`: força cenário `BLOCKED_BY_RISK` para teste.
- outputs operacionais esperados: `NO_ACTION`, `CANDIDATE_SELECTED`, `BLOCKED_BY_MARKET`, `BLOCKED_BY_RISK`.
- no payload, validar `market_debug`:
  - `sample_age_ms`
  - `max_valid_age_ms`
  - `max_degraded_age_ms`
  - `market_assessment_state`
  - `reason_code`
  - `decision_market_ready`

Exemplos reais:
- `safe`:
```bash
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle \
  -H "Content-Type: application/json" \
  -d '{"requested_by":"operator-cli","role":"operator"}' \
  | python3 -m json.tool
```
esperado: `accepted=false`, `decision.operational_output=NO_ACTION`, `intent=null`.
pré-condição recomendada: executar primeiro `POST /api/external/inject-demo-quote-to-market` para garantir sample recente.

- `test`:
```bash
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle \
  -H "Content-Type: application/json" \
  -d '{"mode":"test","requested_by":"operator-cli","role":"operator"}' \
  | python3 -m json.tool
```
esperado (com MARKET válido e sem block de risco): `decision.operational_output=CANDIDATE_SELECTED`, `intent` preenchido, ledger atualizado.
pré-condição recomendada: executar primeiro `POST /api/external/inject-demo-quote-to-market`.

- `force_risk_block=true`:
```bash
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle \
  -H "Content-Type: application/json" \
  -d '{"mode":"test","force_risk_block":true,"requested_by":"operator-cli","role":"operator"}' \
  | python3 -m json.tool
```
esperado: `accepted=false`, `decision.operational_output=BLOCKED_BY_RISK`, `intent=null`.

- `market rejected / sem market válido`:
```bash
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle \
  -H "Content-Type: application/json" \
  -d '{"mode":"test","force_market_rejected":true,"requested_by":"operator-cli","role":"operator"}' \
  | python3 -m json.tool
```
esperado: `accepted=false`, `decision.operational_output=BLOCKED_BY_MARKET`, `reason_summary=market_rejected_forced_for_test`, `intent=null`.

Interpretação de `feed_stale`:
- se `market_debug.reason_code=feed_too_stale`, o sample do market ficou antigo (`sample_age_ms > max_degraded_age_ms`);
- nesse caso, repetir `POST /api/external/inject-demo-quote-to-market` imediatamente antes do `run-decision-cycle`.

8. `POST /api/logs/export`
- esperado: resposta do comando `export-logs`.
- verificar artefacto exportado no caminho pedido.

## E. Logs e ficheiros para troubleshooting
- audit da consola: `"$HOME/odin-runtime/runtime/logs/operator-console-audit.jsonl"`
- audit de external data: `"$HOME/odin-runtime/runtime/logs/external-data-audit.jsonl"`
- audit de decision cycle: `"$HOME/odin-runtime/runtime/logs/decision-cycle-audit.jsonl"`
- status público CORE: `"$HOME/odin-runtime/runtime/state/core_public_view.json"`
- execution ledger (persistência): `runtime/state/core_state.db` tabela `execution_ledger`
  - leitura rápida por API: `GET /api/status` em `execution_summary.last_execution` e `execution_summary.recent_executions`
  - leitura direta SQLite:
```bash
sqlite3 "$HOME/odin-runtime/runtime/state/core_state.db" "select recorded_at_utc, payload_json from execution_ledger order by recorded_at_utc desc limit 5;"
```
- ciclo de vida CORE: `runtime/logs/core-daemon-lifecycle.jsonl`
- ciclo de vida consola: `runtime/logs/operator-console-lifecycle.jsonl`

Campos de debug de idade/prontidão:
- `inject-demo-quote-to-market`: resposta HTTP contém `sample_age_ms`, `max_valid_age_ms`, `market_assessment_state`, `decision_market_ready`;
- `run-decision-cycle`: resposta HTTP e `decision-cycle-audit.jsonl` incluem `market_debug` com `sample_age_ms`, `max_*_age_ms`, `reason_code` e `decision_market_ready`.

Observação em tempo real:
```bash
scripts/odin_trace.sh
```

Com polling detalhado (inclui `read_query`):
```bash
scripts/odin_trace.sh --verbose
```

## F. Reset limpo entre testes (instalação isolada)
Executar sempre primeiro em simulação:

```bash
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh --dry-run
```

Aplicar purge:

```bash
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh
```

Opcional:
- remover também config local:
```bash
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh --remove-config
```
- remover instalação completa:
```bash
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh --remove-install
```

## Validação final obrigatória
```bash
pytest -q
ruff check src tests
mypy src tests
```

Notas:
- este corte não ativa trading real;
- este corte não liga execução real XTB/MT5/OpenAI.
- handoff operacional de sessão: [`docs/runbooks/ODIN-SESSION-HANDOFF.md`](/home/vdo/Secretária/Projects_Codex/Odin_Teste/docs/runbooks/ODIN-SESSION-HANDOFF.md)
