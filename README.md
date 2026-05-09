# ODIN

ODIN é uma plataforma local para decisão operacional, supervisão, auditoria e diagnóstico em trading assistido.

## Estado atual
- Release: **RC1.4 Shadow Runtime Loop & Observability**
- Branch principal: `release/rc1`
- Modo operacional de referência: `SHADOW_MT5`

## Segurança (bloqueios ativos)
- Trading real bloqueado.
- `MT5 order_send` bloqueado.
- XTB real bloqueado.
- Broker real bloqueado.
- LLM sem execução direta.
- ATLAS sem execução direta.
- Runtime sem execução real.
- OpenAI desligada por defeito.

## Componentes RC1
- `odin_control`
- `odin_core`
- `odin_health`
- `odin_assistant`
- `odin_atlas`
- `odin_execution`
- `odin_brokers`
- Dashboard HTML (`apps/dashboard_html`)
- CLI terminal (`apps/dashboard_terminal`)
- Telegram bot (`apps/telegram_bot`)

## Shadow Runtime Loop
O runtime em sombra mantém heartbeat, healthchecks periódicos, snapshot de estado e eventos observáveis sem executar ordens.

### Comandos runtime
```bash
./run_odin.sh --runtime
./run_odin.sh --run-once
./run_odin.sh --runtime-smoke-test
./run_odin.sh --snapshot
python -m apps.dashboard_terminal.cli runtime-status
python -m apps.dashboard_terminal.cli runtime-run-once
python -m apps.dashboard_terminal.cli runtime-snapshot
python -m apps.dashboard_terminal.cli runtime-events
```

### Snapshot e eventos
- Snapshot: `data/runtime/odin_state_snapshot.json`
- Heartbeat: `data/runtime/odin_heartbeat.json`
- Eventos: `data/runtime/odin_events.jsonl`

## Local LLM Assistant
- Provider suportado: `ollama` (opcional).
- Uso: respostas operacionais, explicação de estado e apoio a análise/critica.
- Se indisponível, o Assistant usa fallback seguro sem crash.
- O LLM não executa ordens, não altera configurações críticas e não ignora Command Bus/Risk Engine.

## Como testar (offline/safe)
```bash
./install.sh --dry-run
./healthcheck.sh --offline-ok
./run_odin.sh --smoke-test
./run_odin.sh --runtime-smoke-test
./run_odin.sh --run-once
python -m apps.dashboard_html.app --smoke-test
python -m apps.dashboard_terminal.cli smoke-test
python -m apps.telegram_bot.bot --dry-run
```

## Runbooks
- MT5 Shadow: [docs/runbooks/MT5_SHADOW_MODE.md](docs/runbooks/MT5_SHADOW_MODE.md)
- Local LLM Runtime: [docs/runbooks/LOCAL_LLM_RUNTIME.md](docs/runbooks/LOCAL_LLM_RUNTIME.md)
- Shadow Runtime Loop: [docs/runbooks/SHADOW_RUNTIME_LOOP.md](docs/runbooks/SHADOW_RUNTIME_LOOP.md)

## Aviso
ODIN RC1 **não executa dinheiro real**.
