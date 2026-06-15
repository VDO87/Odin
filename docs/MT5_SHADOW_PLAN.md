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

Proibido:

- Trading real.
- Chamar `mt5.order_send`.
- Simular autorizacao real no Dashboard.
- Ignorar bloqueios do Risk Engine.
