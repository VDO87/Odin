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

## Autorizacao persistente ODIN AUTONOMOUS DEMO OPERATIONS RC2

Esta secao e mais recente e complementa a excecao RC1. Depois do primeiro
canary completo e reconciliado, Codex pode preparar, testar e operar o runtime
DEMO limitado RC2 sem pedir confirmacao por trade. Esta autoridade nao alarga o
escopo da unica chamada isolada e nao permite REAL.

Cada proposta continua sujeita ao Risk Engine, Demo Execution Gate,
`order_check`, reserva atomica, identidade live e reconciliacao. O escopo e
fixado em OANDA TMS DEMO/OANDATMS-MT5, terminal allowlisted, EURUSD/EURUSD.pro,
0.01, uma posicao, uma ordem em voo, tres trades concluidos/dia e perda diaria
realizada maxima de 5 EUR. Qualquer evidencia ausente, estado ambiguo, timeout,
conta REAL/UNKNOWN, fallback ou identidade divergente bloqueia novos envios.

Supervisor, Hermes, LLM, Strategy, n8n e dashboard nao podem chamar
`order_send` diretamente. O supervisor e o dashboard podem permanecer
persistentes em monitor-only ou paused, mas nunca podem ativar Algo Trading no
terminal, enfraquecer limites ou alterar `safe_to_trade=false`,
`real_trading=false` e `execution_allowed=false`.

Nao fazer merge automatico desta branch.
