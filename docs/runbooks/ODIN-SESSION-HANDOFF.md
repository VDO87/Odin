# ODIN Session Handoff

Data de referência: 2026-04-28

## 1. Estado atual resumido
- Odin tem Operator Console funcional.
- Instalação isolada recomendada em `$HOME/odin-runtime`.
- Profile default: `lite`.
- Execução: `demo`.
- Sem trading real.
- Sem `MT5`/`XTB`/`OpenAI` ativos.
- External Data usa `DemoProvider` em `lite`.
- AnythingLLM deve ser tratado como **não integrado operacionalmente** neste handoff (advisory futuro); a chave mencionada em conversa deve ser considerada comprometida e revogada.

## 2. O que já está implementado
- profiles `lite`/`standard`/`full`.
- instalação isolada por defeito.
- `scripts/odin_purge.sh` com guardrails.
- `scripts/odin_trace.sh`.
- Operator Console.
- dashboard multi-página.
- `ExternalDataService` com `DemoProvider`.
- endpoints:
  - `GET /api/status`
  - `GET /api/health`
  - `GET /api/config`
  - `GET /api/external/status`
  - `GET /api/external/quote?symbol=EURUSD`
  - `GET /api/external/calendar`
  - `POST /api/external/inject-demo-quote-to-market`
  - `POST /api/test/run-decision-cycle`
  - `POST /api/commands/pause`
  - `POST /api/commands/resume`
  - `POST /api/commands/stop`
  - `POST /api/logs/export`
- DECISION v1 scenario pack:
  - `safe -> NO_ACTION`
  - `test -> CANDIDATE_SELECTED + intent + ledger`
  - `force_risk_block -> BLOCKED_BY_RISK`
  - `force_market_rejected -> BLOCKED_BY_MARKET`
- execution ledger demo.
- `decision-cycle-audit.jsonl`.
- `external-data-audit.jsonl`.
- `operator-console-audit.jsonl`.

## 3. Validação feita hoje
Resultados registados no ciclo principal de validação de hoje:
- `pytest -q -> 135 passed`
- `ruff check src tests -> All checks passed`
- `mypy src tests -> Success`
- sandbox removido e reinstalado.
- `inject-demo-quote-to-market` aceite.
- `decision safe` devolveu `NO_ACTION`.
- `decision test` com inject imediato devolveu `CANDIDATE_SELECTED + intent + ledger`.
- teste com sample stale devolveu `BLOCKED_BY_MARKET/feed_too_stale`.
- status final mostrou `MARKET Runtime` atualizado.

Validação técnica mais recente no repositório antes do fecho desta sessão:
- `pytest -q -> 139 passed`
- `ruff check src tests -> All checks passed`
- `mypy src tests -> Success`

## 4. Como arrancar amanhã
1. `cd /home/vdo/Secretária/Projects_Codex/Odin_Teste`
2. opcional: validar higiene técnica.
3. instalar/reinstalar sandbox se necessário:
   - `./INSTALL_ODIN.sh --install-root "$HOME/odin-runtime" --profile lite --skip-apt`
4. arrancar consola:
   - `$HOME/odin-runtime/bin/start_operator_console.sh`
5. abrir browser:
   - `http://127.0.0.1:8080`

## 5. Como testar amanhã
```bash
curl http://127.0.0.1:8080/api/status | python3 -m json.tool
curl http://127.0.0.1:8080/api/health | python3 -m json.tool
curl http://127.0.0.1:8080/api/external/status | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/external/inject-demo-quote-to-market | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle | python3 -m json.tool
curl -X POST http://127.0.0.1:8080/api/test/run-decision-cycle -H "Content-Type: application/json" -d '{"mode":"test"}' | python3 -m json.tool
```

## 6. Atenção ao endpoint run-decision-cycle
- campo canónico atual: `mode`.
- `{"mode":"test"}` funciona.
- `{"decision_mode":"test"}` ainda pode não funcionar.
- próximo corte pequeno sugerido:
  - aceitar `decision_mode` como alias de `mode`;
  - rejeitar conflito (`mode` + `decision_mode` diferentes) com `reason_code=ambiguous_decision_mode`.

## 7. Limitações atuais
- Sem trading real.
- Sem MT5 integrado.
- Sem XTB integrado.
- Sem Telegram integrado.
- Sem OpenAI/AnythingLLM integrado operacionalmente.
- Tática DECISION ainda é demo/test, não estratégia lucrativa.
- Dados reais externos não ativos em `lite`.
- Comandos críticos podem exigir confirmação.
- Console-only usa runtime próprio; não correr `start_odin.sh` e `start_operator_console.sh` em paralelo até haver arquitetura clara para isso.

## 8. Próximos passos recomendados por ordem
P0:
- Pequeno corte API: aceitar `decision_mode` como alias de `mode` em `/api/test/run-decision-cycle`.
- Reduzir ruído de polling no trace/recent events, se ainda existir.
- Confirmar e documentar formato de confirmação de `pause`/`resume`/`stop`.

P1:
- DECISION v1.1: estratégia EURUSD M15 Liquidity Sweep/Reversal em demo.
- Criar `CandleSample` / synthetic market sequence.
- Dashboard Decision mostrar fatores positivos/negativos.

P2:
- Intelligence Layer / AnythingLLM advisory.
- Revogar key exposta e usar nova via env `ANYTHINGLLM_API_KEY` ou `config/secrets` ignorado no Git.
- Endpoint `POST /api/intelligence/ask`.
- Bloquear ações críticas da IA.

P3:
- Telegram bridge.
- MT5 demo adapter.
- XTB assisted workflow para ETFs/ações/FIRE.

## 9. Segurança
- Não guardar API keys no Git.
- Confirmar `.gitignore` com:
  - `config/secrets/`
  - `*.secrets.toml`
  - `.env`
- Tratar a chave AnythingLLM citada na conversa como comprometida: revogar e recriar localmente.
- AnythingLLM apenas advisory, sem autoridade `CORE/RISK/EXEC`.

## 10. Comandos de validação final
```bash
./.venv/bin/pytest -q
./.venv/bin/ruff check src tests
./.venv/bin/mypy src tests
```

## 11. Notas finais de retoma
- Sandbox (`$HOME/odin-runtime`) é descartável; fonte de verdade é o repositório principal.
- Se surgir bug em sandbox: corrigir no repositório principal, reinstalar sandbox e repetir validação.

