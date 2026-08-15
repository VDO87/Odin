# OANDA Practice — P0 somente leitura

Este adaptador é uma fonte de dados histórica P0, não uma integração de trading.
Mantém permanentemente `safe_to_trade=false`, `real_trading=false` e
`execution_allowed=false`.

## Limite técnico

- origem fixa: `https://api-fxpractice.oanda.com`;
- único pedido remoto permitido: `GET /v3/accounts/{accountID}/instruments/EUR_USD/candles`;
- parâmetros P0: `EUR_USD`, `price=B`, `granularity=M1`, UTC e um mês histórico
  completo fechado; a preferência atual é
  `[2026-07-01T00:00:00Z, 2026-08-01T00:00:00Z)`;
- não existem chamadas a endpoints de execução, posição, transação ou configuração;
- o adaptador usa apenas a biblioteca padrão Python, sem SDK nem downloader externo.

A [documentação oficial de candles](https://developer.oanda.com/rest-live-v20/pricing-ep/)
define o endpoint e os parâmetros. O ambiente Practice é o host oficial de teste
indicado no [guia de desenvolvimento](https://developer.oanda.com/rest-live-v20/development-guide/).

## Proveniência e persistência

Cada aquisição é dividida deterministicamente em janelas inferiores a 5.000 M1.
As respostas JSON originais são conservadas sem alteração, cada página recebe
SHA-256 e o lote recebe SHA-256 com framing de comprimento. Só depois da
descodificação, verificação UTC/BID, cobertura completa, continuidade e agregação
determinística M1→M15 são persistidos os artefactos em
`D:\ODIN_LOCAL\artifacts\market-data`. O manifesto M15 referencia o hash e o
diretório RAW M1.

## Configuração local posterior à autorização humana

No `.env` local WSL, ignorado pelo Git, definir sem aspas nem espaços:

```dotenv
ODIN_OANDA_PRACTICE_ACCOUNT_ID=<identificador da conta Practice>
ODIN_OANDA_PRACTICE_TOKEN=<token pessoal>
ODIN_OANDA_PRACTICE_API_LICENSE_URL=<URL HTTPS do acordo API aplicável à divisão da conta>
```

O token é tratado como password pela documentação oficial. Nunca o colocar em
Git, logs, JSONL, SQLite, relatórios, HTML, screenshots, exceções ou Hermes.
O campo `license` é preenchido somente com a URL HTTPS do acordo API aplicável
que o titular da conta aceitou; o adaptador bloqueia se essa URL não for um URL
legal oficial OANDA.
