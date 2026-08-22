# Risk Policy

O Risk Engine e autoridade superior para risco operacional e financeiro.

Politicas:

- Estado inicial: bloqueado para real.
- Falta de configuracao de risco implica bloqueio.
- Falta de logs auditaveis implica bloqueio.
- Qualquer tentativa de execucao real sem aprovacao implica bloqueio.
- Hermes nao pode reduzir, contornar ou aprovar risco.
- Dashboard deve reflectir bloqueios de risco sem suavizar linguagem.
- A9 Decision Intent nao aprova risco: `risk_approved=false` por desenho.
- A10 Risk Gate bloqueia tudo por defeito: `risk_status=BLOCKED`.
- A11 Shadow Proposal depende do Risk Gate e permanece bloqueada quando o risco esta bloqueado.
- A12 Runtime Smoke confirma que o estado de risco e bloqueios continuam activos.

## ODIN DEMO EXECUTION RC1

A autorização DEMO é local ao `Demo Execution Gate`; não altera os guardrails
globais. `safe_to_trade=false`, `real_trading=false` e
`execution_allowed=false` permanecem invariantes. Uma conta `REAL` ou
`UNKNOWN`, qualquer divergência de terminal/broker/server/login, fallback de
conta, reconciliação incompleta ou kill switch ativo produz bloqueio antes do
adapter.

Limites conservadores por defeito:

- risco máximo estimado por operação: EUR 10;
- perda diária DEMO máxima: EUR 50;
- drawdown DEMO máximo: 5%;
- posição máxima: 0,01 lot;
- posições e ordens simultâneas: uma de cada;
- free margin mínima: EUR 1.000;
- spread máximo EURUSD: 0,00030;
- freshness máxima: 60 segundos;
- retries máximos declarados: 1, mas qualquer timeout após submissão exige
  reconciliação e nunca é reenviado automaticamente;
- slippage máxima para construir a ordem: 20 points;
- SL e TP obrigatórios, direcionais e respeitando o stop level do símbolo.

O volume inicial é fixo em 0,01 lot e tem ainda de respeitar `volume_min`,
`volume_max` e `volume_step` publicados pelo MT5. O cálculo de perda usa a
distância ao SL, `trade_tick_size`, `trade_tick_value_loss` e volume. Não existe
Kelly, martingale, grid, averaging down ou aumento de risco após perda.

Mesmo `ALLOW_DEMO` só permite avançar para o gate. `order_check` não substitui
o Risk Engine. A primeira submissão CANARY exige uma autorização humana
específica, curta, one-shot, ligada à proposta e ao fingerprint da conta DEMO.
Não há promoção nem reutilização para conta REAL.
