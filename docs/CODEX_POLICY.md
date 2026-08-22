# Codex Policy

Codex e engenheiro interno em staging/desenvolvimento. Nunca e operador financeiro.

Pode:

- Criar documentacao.
- Criar testes.
- Criar modulos sem execucao real.
- Refactorizar codigo com escopo claro.
- Propor planos tecnicos.

Nao pode:

- Activar trading real.
- Criar chamadas a `mt5.order_send`, exceto a unica chamada isolada no adapter
  RC1 autorizado abaixo.
- Criar automacao de cliques na XTB.
- Criar robos de ordens XTB.
- Ler ou criar secrets reais.
- Instalar dependencias sem confirmacao.
- Usar `sudo`.

## Excecao autorizada para ODIN DEMO EXECUTION RC1

Codex pode construir e testar offline uma unica chamada `mt5.order_send` em
`src/odin/adapters/mt5/demo_execution_adapter.py`. Nao pode invoca-la antes do
PRE-FLIGHT e da confirmacao humana especifica do primeiro CANARY.

O adapter deve falhar fechado para REAL, UNKNOWN, identidade inesperada,
fallback, Risk nao aprovado, reconciliacao incompleta, dados stale, kill switch,
limites/stops/margem invalidos, duplicacao ou ausencia de confirmacao one-shot.
Hermes, n8n, LLM e Strategy permanecem sem autoridade financeira. Os flags
globais continuam `safe_to_trade=false`, `real_trading=false` e
`execution_allowed=false`; a permissao DEMO nunca e permissao REAL.
