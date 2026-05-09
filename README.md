# ODIN

ODIN é uma plataforma local para decisão operacional, supervisão, auditoria e diagnóstico em trading assistido.

## Estado atual
- Release: **RC1.2 MT5 Shadow**
- Branch principal recomendada: `release/rc1`
- Modo operacional de referência: `SHADOW_MT5`

## Segurança (bloqueios ativos)
- Trading real bloqueado.
- `MT5 order_send` bloqueado.
- XTB real bloqueado.
- Broker real bloqueado.
- LLM sem execução direta.
- ATLAS sem execução direta.

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

## Aviso
ODIN RC1 **não executa dinheiro real**.
