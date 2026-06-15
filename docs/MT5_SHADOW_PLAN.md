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
- A15 so pode criar mapeamento mock de simbolos, sem terminal real e sem execucao.
- Comando A15 permitido: `python3 -m odin.cli mt5-symbols`.
- Endpoint A15 permitido: `GET /mt5/symbols`.
- A16 so pode criar feed de mercado mock baseado no mapeamento A15.
- Comando A16 permitido: `python3 -m odin.cli mt5-feed`.
- Endpoint A16 permitido: `GET /mt5/feed`.
- Simbolos A16 permitidos: `EURUSD`, `USDJPY` e `GBPUSD`; ativos FIRE ficam excluidos.
- A17 so pode criar gates de qualidade sobre o feed MT5 mock.
- Comando A17 permitido: `python3 -m odin.cli mt5-feed-quality`.
- Endpoint A17 permitido: `GET /mt5/feed/quality`.
- A18 so pode criar selecao mock de fonte observacional entre `market_data_mock` e `mt5_feed_mock`.
- Comando A18 permitido: `python3 -m odin.cli feed-source`.
- Endpoint A18 permitido: `GET /feed/source`.

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
- Transformar mapeamento de simbolos em autorizacao para trading.
- Transformar ticks mock em decisao, risco aprovado ou execucao.
- Transformar gates de qualidade em permissao de decisao ou execucao.
- Transformar selecao de fonte em permissao de decisao ou execucao.
