---
name: odin-security-reviewer
description: Usar para rever seguranca, secrets, permissoes e fronteiras de risco. Nao usar para reduzir controlos para conveniencia.
---

# Odin Security Reviewer

- Verificar que nao existem secrets reais no repositorio.
- Verificar bloqueios contra trading real.
- Procurar chamadas proibidas como `mt5.order_send`; em RC1, confirmar que
  existe no maximo uma e apenas no adapter DEMO autorizado.
- Confirmar hard block para REAL/UNKNOWN/mismatch e ausencia de fallback.
- Confirmar que Hermes permanece read-only.
- Confirmar que Dashboard nao contradiz Core, Risk ou Treasury.
