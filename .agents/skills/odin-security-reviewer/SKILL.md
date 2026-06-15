---
name: odin-security-reviewer
description: Usar para rever seguranca, secrets, permissoes e fronteiras de risco. Nao usar para reduzir controlos para conveniencia.
---

# Odin Security Reviewer

- Verificar que nao existem secrets reais no repositorio.
- Verificar bloqueios contra trading real.
- Procurar chamadas proibidas como `mt5.order_send`.
- Confirmar que Hermes permanece read-only.
- Confirmar que Dashboard nao contradiz Core, Risk ou Treasury.
