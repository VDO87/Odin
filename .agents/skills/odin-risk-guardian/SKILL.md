---
name: odin-risk-guardian
description: Usar para criar, rever ou testar regras de risco. Nao usar para justificar bypasses ou desbloquear trading real.
---

# Odin Risk Guardian

- Risk Engine vence sempre Hermes.
- Falta de limites, logs ou aprovacao implica bloqueio.
- Fora de ODIN DEMO EXECUTION RC1, nunca criar chamadas a `mt5.order_send`.
- Em RC1, permitir no maximo uma chamada no adapter DEMO isolado; exigir conta
  DEMO provada, Risk aprovado, reconciliacao, limites, kill switch e confirmacao
  CANARY one-shot. REAL/UNKNOWN/mismatch sao `HARD_BLOCK`.
- A permissao DEMO nunca altera `real_trading=false` nem os flags globais.
- Nunca permitir automacao de ordens XTB.
- Testar sempre estados bloqueados antes de estados permissivos.
