# P0 — exportação Dukascopy EURUSD M15

Fonte aprovada para o P0: [Dukascopy Historical Data Export](https://widgets.dukascopy.com/en/historical-data-export), exclusivamente para uso interno ODIN em DEMO/replay, sem redistribuição.

Verificação de granularidade em 2026-08-15: o widget oferece a seleção M15, mas o contrato público de `EUR/USD` no respetivo backend JETTA anuncia apenas `MINUTE`, `HOUR` e `DAY`. Por isso o ODIN não assume M15 nativo: transfere somente M1 `BID` do mesmo backend e cria M15 UTC por agrupamento determinístico de janelas completas de 15 candles M1. Janelas incompletas, payloads inconsistentes, OHLC inválido ou ordenação inválida bloqueiam a importação.

Configuração P0: `EUR/USD`, lado `BID`, origem M1, destino M15, timezone `UTC` e um mês calendário completo fechado. O intervalo preferido atual é `[2026-07-01T00:00:00Z, 2026-08-01T00:00:00Z)`; julho de 2025 era apenas um dataset de validação inicial. A origem, formato JSON comprimido do widget, data de download, intervalo, timezone, hash e proveniência ficam no CSV canónico e manifesto aceites. Não são recolhidos nem guardados cookies ou credenciais.

Termos aplicáveis: [Dukascopy Terms of Use](https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/). Esta referência não substitui os termos; o conjunto não é redistribuído.

## Aquisição automática limitada

O comando `odin dukascopy-eurusd-m15-import` faz no máximo três pedidos para cada recurso. Um HTTP 429 é um bloqueio externo transitório, nunca um candle nem um erro do importador: respeita `Retry-After` quando o servidor o fornece; sem esse cabeçalho espera aproximadamente 30 s e depois 60 s, com jitter de até 5 s. Ao terceiro 429 termina em `SOURCE_RATE_LIMITED`; não há retries infinitos e os dados que estejam apenas em memória não são persistidos.

Não foi aceite qualquer dataset automático nesta sessão: o fornecedor devolveu 429 e não existe artefacto P0 válido proveniente dessa tentativa.

## Fallback manual oficial (uma única exportação)

1. Abra [Dukascopy Historical Data Export](https://widgets.dukascopy.com/en/historical-data-export) e escolha `Forex` → `EUR/USD`, lado `BID`, o mês P0 completo aprovado (preferência atual: `2026-07-01 00:00` até `2026-08-01 00:00`), granularidade `M1` e timezone `UTC`/`GMT` explicitamente. Exporte uma única vez em CSV. Não regrave, não filtre e não reformate o ficheiro; não forneça credenciais ou cookies ao ODIN.
2. Coloque o ficheiro original em `D:\ODIN_LOCAL\inbox\dukascopy\EURUSD_M1_BID_UTC_YYYY-MM.csv`, substituindo `YYYY-MM` pelo mês exportado. Este é input externo, não um artefacto aceite; o ODIN não o copia para `artifacts`.
3. Registe a hora UTC real em que fez a exportação e execute, substituindo apenas `AAAA-MM-DDTHH:MM:SSZ` pela hora real:

```powershell
wsl -d Ubuntu-ODIN --user odin --exec sh -lc "cd /home/odin/projects/odin && python3 -m odin.cli dukascopy-eurusd-m1-manual-import --csv /mnt/d/ODIN_LOCAL/inbox/dukascopy/EURUSD_M1_BID_UTC_YYYY-MM.csv --acquired-at-utc AAAA-MM-DDTHH:MM:SSZ --source-url https://widgets.dukascopy.com/en/historical-data-export --terms-url https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/ --artifact-root /mnt/d/ODIN_LOCAL"
```

O fallback aceita somente o cabeçalho CSV oficial `UTC,Open,High,Low,Close,Volume`, timestamps UTC, `EUR/USD` M1 BID estritamente ordenado e OHLCV finito. Deriva período a partir do próprio ficheiro, agrega M1→M15 UTC apenas em janelas completas e passa pelo mesmo contrato P0 fail-closed (schema, manifesto, hash, gaps, duplicados, ordering, OHLC e timezone). O manifesto aceite regista método `Dukascopy Historical Data Export`, URL de fonte, data de aquisição, símbolo, período derivado, UTC, referência dos termos, formato e proveniência. Só o CSV canónico e manifesto aceites são persistidos em `D:\ODIN_LOCAL\artifacts\market-data`.

Depois de uma importação `VALIDATED`, valide `GET /data/history/canonical` no TradeDesk e use o artefacto no replay. Até lá, P0 permanece aberto e `safe_to_trade=false`, `real_trading=false`, `execution_allowed=false`.
