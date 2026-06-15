---
name: odin-risk-guardian
description: Usar para criar, rever ou testar regras de risco. Nao usar para justificar bypasses ou desbloquear trading real.
---

# Odin Risk Guardian

- Risk Engine vence sempre Hermes.
- Falta de limites, logs ou aprovacao implica bloqueio.
- Nunca criar chamadas a `mt5.order_send`.
- Nunca permitir automacao de ordens XTB.
- Testar sempre estados bloqueados antes de estados permissivos.
