# MT5 Shadow Plan

MT5 fica limitado a observacao e shadow nesta fase.

Permitido:

- Market Watch.
- Recolha de dados aprovada.
- Shadow Decision.
- Futuro modo demo, apos aprovacao.
- Dados mock A5 para validar contratos e dashboard sem ligacao real.
- Modo A6 `MARKET_WATCH` apenas observacional com dados mock.
- Gates A7 validam qualidade de dados mock antes de qualquer fase futura.
- A8 adiciona baseline de estrategia apenas observacional, sem sinais ou propostas.
- A9 adiciona intencao de decisao bloqueada, sem parametros de ordem ou execucao.
- A10 adiciona Risk Gate bloqueante, sem aprovacao de risco ou execucao.
- A11 adiciona Shadow Proposal bloqueada, sem ordem shadow executavel.

Proibido:

- Trading real.
- Chamar `mt5.order_send`.
- Simular autorizacao real no Dashboard.
- Ignorar bloqueios do Risk Engine.
