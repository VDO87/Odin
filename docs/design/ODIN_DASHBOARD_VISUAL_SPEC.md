# ODIN Dashboard Visual Spec (RC1.6)

## 1) Estilo alvo
- Terminal trading command center.
- Fundo escuro com contraste técnico.
- Painéis modulares com borders visíveis.
- Texto compacto e monoespaçado.
- Gráfico central simples (sparkline/ASCII quando necessário).
- Logs em formato consola.
- Command bar com acções seguras.
- Alertas de segurança sempre visíveis.

## 2) Inspiração visual
- Dashboards terminal/TUI.
- Painéis estilo BitVision e multi-janelas técnicas.
- Layout de operação (não estilo marketing site).
- Sem aparência genérica de website.

## 3) Informação obrigatória no ecrã principal
- ODIN mode.
- Runtime state.
- Heartbeat.
- `safe_to_trade`.
- Trading real bloqueado.
- MT5 status.
- ATLAS status.
- LLM status.
- Broker Router status.
- Risk Engine status.
- Posições MT5/reconciliação.
- Eventos/logs recentes.
- Campo “Perguntar ao ODIN”.

## 4) Critério mínimo operacional
- Operador percebe estado geral do ODIN em menos de 30 segundos.
- Comandos perigosos não aparecem como acções rápidas.
- “TRADING REAL: BLOCKED” permanece sempre visível.
