# P0 — exportação Dukascopy EURUSD M15

Fonte aprovada para o P0: [Dukascopy Historical Data Export](https://widgets.dukascopy.com/en/historical-data-export), exclusivamente para uso interno ODIN em DEMO/replay, sem redistribuição.

Verificação de granularidade em 2026-08-15: o widget oferece a seleção M15, mas o contrato público de `EUR/USD` no respetivo backend JETTA anuncia apenas `MINUTE`, `HOUR` e `DAY`. Por isso o ODIN não assume M15 nativo: transfere somente M1 `BID` do mesmo backend e cria M15 UTC por agrupamento determinístico de janelas completas de 15 candles M1. Janelas incompletas, payloads inconsistentes, OHLC inválido ou ordenação inválida bloqueiam a importação.

Configuração fixa: `EUR/USD`, lado `BID`, origem M1, destino M15, timezone `UTC`, período `[2025-07-01T00:00:00Z, 2025-08-01T00:00:00Z)`. É um mês calendário completo, com cinco semanas de mercado e mais de duas mil candles M15: suficiente para validação da baseline sem recolher um histórico excessivo. A origem, formato JSON comprimido do widget, data de download, intervalo, timezone, hash e proveniência ficam no CSV canónico e manifesto aceites. Não são recolhidos nem guardados cookies ou credenciais.

Termos aplicáveis: [Dukascopy Terms of Use](https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/). Esta referência não substitui os termos; o conjunto não é redistribuído.

O único comando de ingestão é `odin dukascopy-eurusd-m15-import`; ele chama obrigatoriamente o importador canónico fail-closed. Só o CSV aceite e o seu manifesto são persistidos em `D:\ODIN_LOCAL\artifacts\market-data`.
