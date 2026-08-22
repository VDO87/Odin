---
name: odin-mt5-shadow
description: Usar para Market Watch, Shadow Decision e ODIN DEMO EXECUTION RC1. Nao usar para trading real; `mt5.order_send` so pode existir no adapter DEMO isolado e human-gated.
---

# Odin MT5 Shadow

- Manter Market Watch e Shadow Decision sem acesso ao adapter de execucao.
- Proibir `mt5.order_send` em todo o codigo salvo a unica chamada no adapter
  ODIN DEMO EXECUTION RC1 explicitamente autorizado.
- Nao criar execucao real.
- Separar dados observados de decisoes simuladas.
- Conta REAL/UNKNOWN/mismatch e `HARD_BLOCK`; sem PRE-FLIGHT e confirmacao
  humana CANARY one-shot, DEMO termina antes do envio.
