# SDS-200 — MARKET
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Arquitetura técnica do módulo MARKET, ingestão de dados, validação de integridade, classificação de contexto, spread adaptativo, guardas macroeconómicas, heartbeat e publicação de estado para os módulos dependentes.

---

## 1. Finalidade do documento

Este documento define a especificação técnica do módulo **MARKET** do Odin.

Se o FSD-200 define **o que o MARKET deve fazer**, este SDS-200 define **como o MARKET deverá ser estruturado tecnicamente** para:
- receber dados de mercado;
- validar integridade e frescura;
- classificar o estado do mercado;
- classificar o contexto resumido;
- detetar degradação e indisponibilidade;
- aplicar filtros preventivos por spread e eventos macro;
- publicar estado e eventos fiáveis para CORE, RISK, DECISION e DASH.

O MARKET não decide nem executa. O seu papel técnico é produzir uma **verdade operacional do mercado** suficientemente robusta para que o resto do sistema não opere sobre ilusão, atraso ou liquidez enganadora.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- arquitetura lógica interna do módulo MARKET;
- pipeline de ingestão e normalização;
- validação temporal e estrutural de dados;
- modelo técnico de feed state e context state;
- spread adaptativo;
- event/news guard;
- heartbeat/liveness do módulo;
- publicação de estado resumido;
- interfaces técnicas com CORE, RISK, DECISION e DASH;
- políticas de timeout, degradação e fail-safe;
- testes técnicos mínimos.

### 2.2 Excluído
Este documento não inclui:
- algoritmo de decisão;
- limites de risco detalhados;
- execução broker-specific;
- design visual do dashboard;
- modelo matemático avançado de previsão;
- integração multi-broker final.

---

## 3. Objetivos técnicos

O módulo MARKET deverá garantir, no mínimo:

1. **Ingestão robusta**
   Receber e normalizar dados mínimos do mercado alvo com referência temporal consistente.

2. **Validação rigorosa**
   Distinguir feed válido, degradado, inválido e indisponível sem ambiguidade.

3. **Contexto técnico explícito**
   Transformar sinais brutos em estados técnicos consumíveis por CORE, RISK e DECISION.

4. **Proteção contra falsa normalidade**
   Detetar contexto hostil por spread anormal, latência excessiva ou janela macro crítica.

5. **Liveness observável**
   Publicar heartbeat e estado resumido de saúde do próprio módulo.

6. **Fail-safe**
   Em dúvida sobre integridade de dados, degradar ou bloquear em vez de sinalizar normalidade.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-200 — MARKET
- FSD consolidado v0.5
- ODIN-CORE-STATE-AND-EVENT-MODEL
- SDS-100 — CORE
- SDS-120 — CORE-INTERFACES
- ODIN-TRACEABILITY-MATRIX

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| Distinguir mercado válido, degradado, inválido e indisponível | FSD-200 | `MarketStateClassifier` |
| Publicar prontidão funcional clara | FSD-200 | `ReadinessPublisher` |
| Aplicar filtro preventivo de notícias | FSD-200 / v0.3 | `NewsGuardEvaluator` |
| Aplicar spread adaptativo | FSD-200 / v0.4 | `SpreadHealthEvaluator` |
| Produzir contexto resumido favorável/neutro/sensível/hostil/indeterminado | FSD-200 | `ContextClassifier` |
| Liveness crítico do MARKET | v0.4 / SDS-100 | `MarketHeartbeatEmitter` |

---

## 5. Arquitetura lógica do MARKET

O módulo MARKET deverá ser decomposto, no mínimo, nos seguintes componentes técnicos:

| Componente | Responsabilidade técnica |
|---|---|
| `MarketIngestor` | receção de ticks/quotes/eventos externos |
| `MarketProfileGate` | aplicar envelope operacional e filtrar instrumentos/feeds permitidos pelo profile ativo |
| `MarketSampleAdapter` | converter input operacional canónico em `MarketSampleInput` com thresholds efetivos do profile/config |
| `MarketNormalizer` | normalização de payloads e campos canónicos |
| `TimestampValidator` | validação temporal e frescura |
| `FeedIntegrityEvaluator` | validação de integridade estrutural e continuidade |
| `SpreadHealthEvaluator` | análise de spread e liquidez implícita |
| `SessionClassifier` | classificação de sessão/janela de mercado |
| `NewsGuardEvaluator` | avaliação de guardas macroeconómicas |
| `MarketStateClassifier` | cálculo de `MS-*` |
| `ContextClassifier` | cálculo de `MC-*` |
| `ReadinessEvaluator` | cálculo de prontidão funcional |
| `MarketStatePublisher` | publicação de estado/eventos |
| `MarketHeartbeatEmitter` | publicação de heartbeat/liveness |
| `MarketAuditLogger` | logging técnico do módulo |

---

## 6. Modelo técnico de dados base

### 6.1 Unidade mínima de observação de mercado
O MARKET deverá tratar como unidade mínima um registo equivalente a `market_sample`.

#### Campos mínimos do `market_sample`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `sample_id` | Sim | ID único do sample |
| `instrument_id` | Sim | instrumento/par observado |
| `bid` | Sim, se aplicável | bid atual |
| `ask` | Sim, se aplicável | ask atual |
| `mid` | Recomendado | preço médio derivado |
| `spread` | Sim | spread atual |
| `timestamp_source_utc` | Sim | timestamp da origem |
| `timestamp_ingested_utc` | Sim | timestamp de ingestão |
| `source_feed_id` | Sim | origem/feed |
| `sample_quality_flag` | Sim | qualidade básica do sample |

### 6.2 Campos derivados obrigatórios

| Campo | Descrição |
|---|---|
| `sample_age_ms` | idade do sample |
| `latency_ms` | latência estimada da origem à ingestão |
| `spread_ratio` | spread atual / spread de referência |
| `is_market_open_candidate` | sinal preliminar de abertura |
| `has_news_guard` | presença de janela macro crítica |

### 6.3 Envelope operacional por profile

O runtime deve conseguir aplicar, antes do pipeline principal do `MARKET`, um envelope operacional derivado de `settings.market`.

Campos mínimos de governação operacional:

| Campo | Função |
|---|---|
| `instrument_scope` | lista de instrumentos permitidos para ingestão operacional |
| `feed_scope` | lista de feeds permitidos para ingestão operacional |
| `news_guard_enabled` | permite ou força desligar o guard de notícias no adaptador |
| `spread_guard_enabled` | permite ou força desligar o gating por spread no adaptador |
| `heavy_enrichment_enabled` | permite ou força desligar enriquecimento pesado antes do `MarketSampleInput` |

Regra obrigatória do corte atual:
- em `profile=lite`, o envelope efetivo deve ser limitado a `1` instrumento e `1` feed;
- em `profile=lite`, `news_guard_enabled` deve resolver para `false` por defeito;
- em `profile=lite`, `spread_guard_enabled` deve resolver para `true`;
- em `profile=lite`, `heavy_enrichment_enabled` deve resolver para `false`.

Mapeamento obrigatório do corte atual:
- `execution_profile=lite` -> `market_profile=simple`;
- `execution_profile=standard` -> `market_profile=standard`;
- `execution_profile=full` -> `market_profile=full`.

### 6.4 Estado de runtime do gate

Após cada ingestão operacional, o runtime deve conseguir expor um estado equivalente a `MarketRuntimeStatus`, com pelo menos:
- `execution_profile`, `market_profile`;
- `instrument_scope`, `feed_scope`;
- `news_guard_enabled`, `spread_guard_enabled`, `heavy_enrichment_enabled`;
- `last_gate_status`, `last_rejection_reason`;
- `last_instrument_id`, `last_feed_id`;
- `applied_restrictions` e restrições ativas derivadas do envelope efetivo.

---

## 7. Estados técnicos do MARKET

### 7.1 Feed / market state canónico (`MS-*`)

| Código | Nome técnico | Significado |
|---|---|---|
| MS-10 | VALID | dados e contexto mínimos utilizáveis |
| MS-20 | DEGRADED | dados utilizáveis com confiança reduzida |
| MS-30 | INVALID | dados presentes mas funcionalmente inválidos |
| MS-40 | CLOSED | mercado fechado para o contexto operacional |
| MS-50 | UNAVAILABLE | ausência de feed ou indisponibilidade total |

### 7.2 Context state canónico (`MC-*`)

| Código | Nome técnico | Significado |
|---|---|---|
| MC-10 | FAVORABLE | contexto dentro do envelope esperado |
| MC-20 | NEUTRAL | contexto aceitável sem vantagem clara |
| MC-30 | SENSITIVE | contexto sensível / prudência exigida |
| MC-40 | HOSTILE | contexto desfavorável ou perigoso |
| MC-50 | INDETERMINATE | informação insuficiente ou inconsistente |

### 7.3 Prontidão funcional
O MARKET deverá também calcular um estado de prontidão equivalente a:

| Código lógico | Significado |
|---|---|
| `NOT_READY` | não pronto |
| `READY_RESTRICTED` | pronto com restrições |
| `READY` | pronto para consumo operacional normal |
| `UNAVAILABLE` | indisponível |

---

## 8. Pipeline técnico do MARKET

### 8.1 Sequência mínima
Cada ciclo de ingestão deverá seguir, no mínimo:

1. receção do sample bruto;
2. `profile gate` / filtro de instrumento-feed;
3. adaptação para `MarketSampleInput` com thresholds e guards efetivos;
4. validação temporal;
5. validação estrutural;
6. cálculo de spread e métricas derivadas;
7. classificação de sessão;
8. avaliação de news guard;
9. classificação de `MS-*`;
10. classificação de `MC-*`;
11. cálculo de prontidão;
12. publicação de eventos/estado;
13. logging estruturado.

### 8.2 Regra obrigatória
Nenhum evento `EV-MARKET-READY` deve ser emitido antes de concluída a validação mínima do sample/ciclo.

Se o sample falhar no `profile gate`, o pipeline deve rejeitá-lo antes da classificação principal e convergir para estado não pronto.

No runtime atual, este enforcement ocorre dentro de `CoreRuntimeController.ingest_market_sample(...)` via `MarketOperationalPipeline`:
1. `MarketProfileGate.evaluate(sample)` (aceita/rejeita scope e aplica restrições);
2. só em caso de aceitação ocorre adaptação para `MarketSampleInput`;
3. em rejeição, o motivo deve ser explícito (`instrument_scope_rejected` ou `feed_scope_rejected`) e o `CORE` deve receber evento não pronto.

---

## 9. Validação temporal

### 9.1 Objetivo
Garantir que o sistema não trata dados antigos como atuais.

### 9.2 Métricas técnicas mínimas
- `sample_age_ms`
- `latency_ms`
- `last_valid_update_delta_ms`

### 9.3 Thresholds lógicos parametrizáveis
O MARKET deverá suportar, no mínimo:

| Parâmetro | Função |
|---|---|
| `max_valid_age_ms` | idade máxima para estado válido |
| `max_degraded_age_ms` | idade máxima para estado degradado |
| `max_valid_latency_ms` | latência máxima aceitável para estado válido |
| `max_degraded_latency_ms` | latência máxima antes de invalidar |

### 9.4 Regras obrigatórias
- Se `sample_age_ms > max_valid_age_ms`, o estado não pode permanecer `MS-10`.
- Se `sample_age_ms > max_degraded_age_ms`, o estado deve convergir para `MS-30` ou `MS-50`, conforme o caso.
- A ausência de novo sample além da janela de degradação deve contribuir para `MS-50`.

---

## 10. Validação estrutural e integridade

### 10.1 Objetivo
Garantir que o sample e o feed são coerentes o suficiente para consumo funcional.

### 10.2 Verificações mínimas
- campos obrigatórios presentes;
- `bid <= ask` quando aplicável;
- `spread >= 0`;
- timestamps plausíveis;
- instrumento válido;
- origem/feed reconhecido;
- sequência plausível de updates.

### 10.3 Regras obrigatórias
- payload estruturalmente inválido não pode gerar `MS-10`.
- inconsistência repetida deve ser promovida a `MS-30` ou `MS-50`.
- feed intermitente recorrente deve ser tratado como sinal de degradação real.

---

## 11. Spread adaptativo e liquidez implícita

### 11.1 Objetivo
Evitar operar com custos operacionais invisíveis mesmo quando o feed parece vivo.

### 11.2 Métricas obrigatórias
- `spread_current`
- `spread_avg_ref`
- `spread_ratio = spread_current / spread_avg_ref`

### 11.3 Fontes de `spread_avg_ref`
A referência deverá ser parametrizável, permitindo:
- média móvel 24h;
- média por sessão;
- média por janela equivalente configurada.

### 11.4 Thresholds lógicos parametrizáveis

| Parâmetro | Função |
|---|---|
| `spread_multiplier_degraded` | a partir daqui o estado degrada |
| `spread_multiplier_hostile` | a partir daqui o contexto pode ser hostil |
| `spread_absolute_critical` | spread absoluto crítico |
| `spread_reference_window` | janela de cálculo da referência |

### 11.5 Regras obrigatórias
- Feed vivo com `spread_ratio` anormal não deve ser tratado como normal.
- `MS-20` deve poder ser ativado por spread excessivo.
- `MC-40` deve poder ser ativado por spread crítico mesmo sem latência alta.
- Aberturas de domingo, transições de sessão e liquidez fraca devem ser suportadas pelo modelo.

---

## 12. Classificação de sessão

### 12.1 Objetivo
Contextualizar o mercado por janela temporal relevante.

### 12.2 Sessões mínimas suportadas
- `ASIA`
- `EUROPE`
- `US`
- `OVERLAP`
- `LOW_ACTIVITY`
- `UNDETERMINED`

### 12.3 Entradas mínimas
- relógio UTC;
- timezone/política operacional;
- calendário de sessão configurado.

### 12.4 Regras obrigatórias
- Sessão deve influenciar `MC-*`, nunca substituir integridade ou spread.
- `LOW_ACTIVITY` pode contribuir para `MC-30` ou `MS-20`, conforme política.

---

## 13. News guard / filtro macroeconómico

### 13.1 Objetivo
Impedir falsa normalidade antes de eventos de alto impacto.

### 13.2 Entradas mínimas
- `event_time_utc`
- `event_impact_class`
- `event_source_id`
- `guard_window_pre_minutes`
- `guard_window_post_minutes`

### 13.3 Classificações mínimas de impacto
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL` (opcional, mas recomendável)

### 13.4 Regras obrigatórias
- Evento `HIGH` dentro da janela predefinida deve forçar pelo menos `MC-30`.
- Evento `HIGH` ou `CRITICAL` em janela crítica pode forçar `MC-40`.
- A classificação preventiva independe do spread momentâneo estar “calmo”.
- Se a fonte de notícias for obrigatória e estiver indisponível, o contexto deve poder convergir para `MC-50`.

### 13.5 Evento canónico
Quando o guard estiver ativo, o MARKET deverá poder emitir:
- `EV-MARKET-NEWS-GUARD`

---

## 14. Classificador de estado do mercado (`MS-*`)

### 14.1 Regras mínimas de decisão

#### `MS-10 VALID`
Só permitido se:
- sample válido estruturalmente;
- idade dentro do limite válido;
- latência dentro do limite válido;
- feed não marcado como intermitente crítico;
- mercado não fechado;
- sem indisponibilidade total.

#### `MS-20 DEGRADED`
Aplicável quando:
- idade/latência degradadas mas ainda utilizáveis;
- spread excessivo mas não crítico;
- feed intermitente;
- sessão ou contexto reduzem confiança.

#### `MS-30 INVALID`
Aplicável quando:
- sample estruturalmente inválido;
- latência/idade acima do limiar utilizável;
- inconsistência grave do feed;
- informação presente mas não fiável.

#### `MS-40 CLOSED`
Aplicável quando:
- janela de mercado fechada para o instrumento/política em causa.

#### `MS-50 UNAVAILABLE`
Aplicável quando:
- ausência total de feed;
- perda prolongada de atualização;
- fonte crítica indisponível.

---

## 15. Classificador de contexto (`MC-*`)

### 15.1 Regras mínimas de decisão

#### `MC-10 FAVORABLE`
Condições dentro do envelope esperado:
- `MS-10`;
- spread saudável;
- sem guard macro crítico;
- sessão aceitável;
- sem penalizadores relevantes.

#### `MC-20 NEUTRAL`
Condições aceitáveis, mas sem sinal de qualidade superior:
- market válido;
- sem vantagem contextual clara.

#### `MC-30 SENSITIVE`
Contexto sensível quando:
- `MS-20`;
- news guard ativo;
- sessão de baixa atividade;
- spread acima do normal mas ainda não crítico;
- incerteza operacional moderada.

#### `MC-40 HOSTILE`
Contexto hostil quando:
- spread crítico;
- volatilidade contextual excessiva, se essa métrica estiver ativa;
- evento macro de alto impacto em janela crítica;
- feed muito degradado;
- múltiplos penalizadores simultâneos.

#### `MC-50 INDETERMINATE`
Contexto indeterminado quando:
- informação insuficiente;
- fonte crítica ausente;
- estado não classificável com confiança mínima.

### 15.2 Regra obrigatória
`MC-50` nunca deve ser tratado automaticamente como `MC-20`.

---

## 16. Prontidão funcional

### 16.1 Regras mínimas

#### `READY`
- `MS-10`
- contexto não incompatível
- mercado aberto, quando exigido
- sem guard bloqueante configurado

#### `READY_RESTRICTED`
- market utilizável, mas com restrições
- normalmente associado a `MS-20` e/ou `MC-30`

#### `NOT_READY`
- market inválido, fechado ou contexto incompatível

#### `UNAVAILABLE`
- indisponibilidade de feed ou infraestrutura crítica

### 16.2 Regra obrigatória
O MARKET não decide execução, mas a prontidão deve ser suficientemente clara para o CORE e para o RISK.

---

## 17. Heartbeat do módulo MARKET

### 17.1 Objetivo
Permitir ao CORE distinguir:
- módulo MARKET saudável;
- módulo atrasado;
- módulo sem liveness.

### 17.2 Payload mínimo do heartbeat

| Campo | Obrigatório |
|---|---|
| `module_id` | Sim |
| `timestamp_utc` | Sim |
| `market_module_state` | Sim |
| `last_valid_sample_utc` | Recomendado |
| `last_ms_state` | Recomendado |
| `last_mc_state` | Recomendado |
| `health_flag` | Sim |

### 17.3 Regras obrigatórias
- Heartbeat deve ser periódico e parametrizável.
- Heartbeat sem atualização válida do mercado pode continuar a existir, mas deve refletir degradação real.
- O CORE não deve confundir “MARKET vivo” com “mercado utilizável”.

---

## 18. Eventos publicados pelo MARKET

### 18.1 Eventos mínimos
- `EV-MARKET-READY`
- `EV-MARKET-DEGRADED`
- `EV-MARKET-INVALID`
- `EV-MARKET-CLOSED`
- `EV-MARKET-HOSTILE`
- `EV-MARKET-NEWS-GUARD`
- `EV-HB-OK`
- `EV-HB-TIMEOUT` (originado pelo supervisor ou refletido via CORE)

### 18.2 Regras obrigatórias
- Mudança real de `MS-*` ou `MC-*` deve ser publicável como evento relevante.
- O módulo deve evitar “spam” de eventos idênticos sem alteração material.
- O log técnico pode ser mais granular do que o event stream publicado ao CORE.

---

## 19. Interface com CORE

### 19.1 O CORE consome do MARKET
- estado `MS-*`
- contexto `MC-*`
- prontidão
- feed integrity summary
- heartbeat

### 19.2 Payload mínimo publicado ao CORE

| Campo | Obrigatório |
|---|---|
| `market_state` | Sim |
| `context_state` | Sim |
| `readiness_state` | Sim |
| `last_valid_update_utc` | Sim |
| `feed_integrity_state` | Sim |
| `spread_state` | Recomendado |
| `news_guard_active` | Recomendado |

### 19.3 Regras obrigatórias
- O CORE deve poder depender deste contrato sem consultar internamente a lógica do MARKET.
- O MARKET não deve publicar “ready” com payload estruturalmente incompleto.

---

## 20. Interface com RISK

### 20.1 O RISK consome do MARKET
- `MC-*`
- spread state
- news guard
- market open/closed
- feed integrity summary

### 20.2 Regras obrigatórias
- O MARKET deve fornecer ao RISK sinais suficientes para restrição contextual.
- O RISK não deve precisar de recalcular a semântica base do mercado a partir de ticks brutos.

---

## 21. Interface com DECISION

### 21.1 O DECISION consome do MARKET
- último sample válido;
- estado `MS-*`;
- contexto `MC-*`;
- sessão;
- guardas macro;
- referência temporal mínima.

### 21.2 Regras obrigatórias
- O DECISION não deve promover oportunidade executável ignorando o estado do MARKET.
- O MARKET deve fornecer informação temporal suficiente para evitar decisões em dados velhos.

---

## 22. Interface com DASH

### 22.1 O DASH consome do MARKET
- estado do mercado;
- contexto resumido;
- sessão;
- última atualização válida;
- spread state;
- news guard;
- feed integrity summary.
- profile operacional ativo do `MARKET`;
- restrições efetivas aplicadas pelo gate (`instrument_scope`, `feed_scope`, guards desligados e enriquecimento pesado desligado).
- estado do último gate (`last_gate_status`, `last_rejection_reason`, `last_instrument_id`, `last_feed_id`).

### 22.2 Regras obrigatórias
- O DASH deve conseguir mostrar porque o mercado não está utilizável.
- `MS-20`, `MC-30`, `MC-40` e `MC-50` devem ser visíveis sem leitura de logs técnicos.

---

## 23. Logging técnico do MARKET

### 23.1 Campos mínimos
- `timestamp_utc`
- `instrument_id`
- `source_feed_id`
- `sample_id`
- `market_state`
- `context_state`
- `readiness_state`
- `spread`
- `spread_ratio`
- `sample_age_ms`
- `latency_ms`
- `news_guard_active`
- `severity`
- `message`

### 23.2 Eventos obrigatórios a logar
- arranque do módulo;
- perda de feed;
- recuperação de feed;
- mudança de `MS-*`;
- mudança de `MC-*`;
- ativação de news guard;
- trigger de spread degradado/hostil;
- sample inválido estruturalmente;
- timeout/liveness issues.

---

## 24. Persistência local mínima do MARKET

### 24.1 Objetivo
O MARKET não precisa da mesma persistência estrutural do CORE, mas deve conseguir preservar algum contexto mínimo local se a arquitetura assim o exigir.

### 24.2 Itens mínimos recomendados
- último sample válido;
- última referência temporal válida;
- média de spread de referência;
- estado `MS-*` e `MC-*` mais recentes;
- janela de news guard ativa.

### 24.3 Regra
Esta persistência é auxiliar. A autoridade principal de recovery continua a ser o CORE/RECOVERY.

---

## 25. Timeouts e fail-safe

### 25.1 Timeouts mínimos parametrizáveis

| Parâmetro | Função |
|---|---|
| `market_sample_timeout_ms` | tempo sem novo sample antes de degradação |
| `market_unavailable_timeout_ms` | tempo sem novo sample antes de indisponibilidade |
| `market_heartbeat_interval_ms` | intervalo de heartbeat |
| `market_heartbeat_timeout_ms` | timeout de liveness do módulo |

### 25.2 Regras obrigatórias
- Silêncio do feed não pode ser tratado como estabilidade.
- Falta de sample não implica sempre indisponibilidade imediata, mas deve degradar progressivamente.
- Falta de heartbeat do módulo é independente da validade do último sample.

---

## 26. Erros de contrato e rejeição de input

### 26.1 Tipos mínimos
- `invalid_market_sample`
- `invalid_timestamp`
- `invalid_spread`
- `unsupported_source_feed`
- `schema_version_mismatch`
- `missing_required_field`

### 26.2 Regras obrigatórias
- Samples inválidos não devem entrar na cadeia de classificação como se fossem normais.
- Erro de contrato repetido deve ser sinalizado como degradação da origem/feed.

---

## 27. Testes técnicos mínimos

### 27.1 Unit tests
- cálculo de `sample_age_ms`;
- cálculo de `spread_ratio`;
- classificação `MS-*`;
- classificação `MC-*`;
- ativação de news guard;
- prontidão derivada.

### 27.2 Integration tests
- feed válido com mercado aberto;
- mercado fechado;
- feed degradado por latência;
- spread anormal com feed vivo;
- evento macro de alto impacto a 5 minutos;
- perda total de feed;
- recuperação após perda de feed;
- heartbeat saudável vs timeout.

### 27.3 Fault-injection tests
- timestamps invertidos;
- `bid > ask`;
- spread nulo/negativo inválido;
- origem de feed não suportada;
- news source indisponível quando obrigatória.

---

## 28. Critérios de aceitação

O SDS-200 — MARKET será considerado tecnicamente suficiente quando:

1. a arquitetura do módulo suportar ingestão, validação e classificação sem ambiguidades;
2. `MS-*`, `MC-*` e prontidão estiverem tecnicamente definidos;
3. spread adaptativo e news guard estiverem formalizados;
4. o módulo puder publicar estado resumido fiável para CORE, RISK, DECISION e DASH;
5. timeouts e fail-safe do MARKET estiverem definidos;
6. o heartbeat do módulo estiver definido;
7. o documento permitir implementação e testes diretos.

---

## 29. Dependências e próximos documentos

### 29.1 Dependências principais
- SDS-100 — CORE
- SDS-120 — CORE-INTERFACES
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 29.2 Próximos documentos recomendados
1. **SDS-400 — RISK**
2. **SDS-500 — EXEC**
3. **SDS-300 — DECISION**
4. **SDS-600 — DASH**

---

## 30. Conclusão

O SDS-200 transforma o MARKET de conceito funcional em componente técnico sério.

Sem este documento, o sistema arrisca-se a tratar preço, spread, latência e eventos macro como sinais avulsos, o que em Forex é uma receita para operar em contexto errado com falsa confiança.

Com este documento, o MARKET passa a ter:
- pipeline técnico claro;
- critérios explícitos de validade;
- mecanismo de degradação;
- proteção contra custos invisíveis;
- semântica estável para consumo pelos módulos críticos.

Num sistema deste tipo, mercado sem engenharia de integridade não é market data. É risco mascarado.
