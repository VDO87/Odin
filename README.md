# ODIN

ODIN é uma plataforma local para decisão operacional, supervisão, auditoria e diagnóstico em trading assistido.

## Estado atual
- Release: **RC1.3 Local LLM Runtime**
- Branch principal: `release/rc1`
- Modo operacional de referência: `SHADOW_MT5`

## Segurança (bloqueios ativos)
- Trading real bloqueado.
- `MT5 order_send` bloqueado.
- XTB real bloqueado.
- Broker real bloqueado.
- LLM sem execução direta.
- ATLAS sem execução direta.
- OpenAI desligada por defeito.

## Componentes RC1
- `odin_control`
- `odin_health`
- `odin_assistant`
- `odin_atlas`
- `odin_execution`
- `odin_brokers`
- Dashboard HTML (`apps/dashboard_html`)
- CLI terminal (`apps/dashboard_terminal`)
- Telegram bot (`apps/telegram_bot`)

## Local LLM Assistant
- Provider suportado: `ollama` (opcional).
- Uso: respostas operacionais, explicação de estado, apoio a análise/critica.
- Se indisponível, o Assistant usa fallback seguro sem crash.
- O LLM não executa ordens, não altera configurações críticas e não ignora Command Bus/Risk Engine.

### Comandos úteis (CLI)
```bash
python -m apps.dashboard_terminal.cli llm-status
python -m apps.dashboard_terminal.cli ask "Qual é o estado do ODIN?"
python -m apps.dashboard_terminal.cli ask "O ODIN pode operar agora?"
python -m apps.dashboard_terminal.cli ask "Activa trading real"
python -m apps.dashboard_terminal.cli assistant-smoke-test
```

### Dashboard
- Endpoint de assistant: `/assistant` e `/assistant/ask`
- Estado LLM: `/llm/status`

### Telegram
- Comandos: `/llm`, `/llm_status`, `/ask`, `/odin`
- Em `--dry-run`, não há chamadas de rede externas.

## Como testar (offline/safe)
```bash
./install.sh --dry-run
./healthcheck.sh --offline-ok
./run_odin.sh --smoke-test
python -m apps.dashboard_html.app --smoke-test
python -m apps.dashboard_terminal.cli smoke-test
python -m apps.telegram_bot.bot --dry-run
```

## MT5 Shadow
Ver runbook: [docs/runbooks/MT5_SHADOW_MODE.md](docs/runbooks/MT5_SHADOW_MODE.md)

## Local LLM Runtime
Ver runbook: [docs/runbooks/LOCAL_LLM_RUNTIME.md](docs/runbooks/LOCAL_LLM_RUNTIME.md)

## Aviso
ODIN RC1 **não executa dinheiro real**.
