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
- A12 valida localmente a cadeia segura sem ligar ao MT5 real.
- A13 fecha a base `LOCAL_SAFE_RUNTIME` e prepara a release `v0.1.0-local-safe-runtime`.
- A14 so pode criar uma MT5 mock bridge: contrato/adaptador mock e endpoint/status mock, sem MetaTrader5 real.
- Comando A14 permitido: `python3 -m odin.cli mt5-bridge`.
- Endpoint A14 permitido: `GET /mt5/bridge`.

Proibido:

- Trading real.
- Chamar `mt5.order_send`.
- Simular autorizacao real no Dashboard.
- Ignorar bloqueios do Risk Engine.
- Fazer login MT5.
- Usar pacote MetaTrader5 real.
- Transformar shadow proposal em ordem executavel.
- Guardar credenciais.
- Detectar ou ligar a terminal real.
