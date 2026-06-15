---
name: odin-architect
description: Usar para desenhar ou rever arquitectura ODIN/Hermes/Dashboard. Nao usar para implementar execucao real ou alterar regras de risco.
---

# Odin Architect

- Manter Core, Risk, Treasury, Hermes e Dashboard separados.
- Preferir contratos explicitos antes de implementacoes.
- Isolar integracoes externas em `src/odin/adapters`.
- Confirmar que trading real continua bloqueado por defeito.
- Actualizar `docs/ARCHITECTURE_LOCK.md` quando houver decisoes estruturais.
