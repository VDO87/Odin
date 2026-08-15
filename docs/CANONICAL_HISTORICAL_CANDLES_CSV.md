# CSV canónico de candles históricos

Schema atual: `odin.candles.csv/v1`.

O importador `odin.data.canonical_candle_history.import_canonical_candle_history`
aceita apenas CSV UTF-8, com esta ordem exata de colunas:

```text
symbol,timeframe,timestamp_utc,open,high,low,close,volume,source,source_version,schema_version,provenance,license,hash
```

Cada linha contém a mesma identidade de dataset (`symbol`, `timeframe`, origem,
proveniência, licença e versão). `timestamp_utc` tem de terminar em `Z` ou
`+00:00`; os candles têm de estar em ordem estrita, sem duplicados. O único gap
admissível é o encerramento semanal limitado de sexta-feira para domingo.

`hash` é o SHA-256 do conteúdo canónico do dataset, excluindo a própria coluna
`hash`: cabeçalho sem `hash`, seguido das linhas nessa ordem, separado por `\n`
e terminado em `\n`. O mesmo hash é repetido em todas as linhas. Isto torna o
ficheiro autocontido e impede a persistência de dados alterados.

O importador rejeita em modo fail-closed schema/versão, identidade, UTC,
ordenação, duplicados, gaps, OHLCV, `NaN`, infinito, metadados, proveniência e
hash inválidos. Não corrige dados silenciosamente.

Quando válido, é copiado sem alteração para
`D:\\ODIN_LOCAL\\artifacts\\market-data\\<symbol>\\<timeframe>\\<hash>.csv`
(o chamador Windows fornece `D:\\ODIN_LOCAL` como `artifact_root`) juntamente
com um manifesto JSON com período, qualidade, proveniência e instante de
ingestão. Resultados bloqueados não criam artefactos.
