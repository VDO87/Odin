# SDS-500 — EXEC
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Arquitetura técnica do módulo EXEC, validação pré-execução, submissão, controlo de slippage, idempotência, confirmação, reconciliação, divergência e integração com CORE, RISK, DECISION, MARKET e DASH.

---

## 1. Finalidade do documento

Este documento define a especificação técnica do módulo **EXEC** do Odin.

Se o FSD-500 define **o que o EXEC deve fazer**, este SDS-500 define **como o módulo deverá ser construído tecnicamente** para:
- receber intenções operacionais formais;
- revalidar permissões imediatamente antes da submissão;
- respeitar TTL e expiração;
- controlar slippage máximo permitido;
- submeter ações/ordens de forma idempotente;
- classificar resposta inicial e resultado consolidado;
- reconciliar o estado interno com o estado externo;
- sinalizar divergência crítica e escalar para CORE/RECOVERY quando necessário.

O EXEC não escolhe a tática nem redefine risco. O seu papel técnico é fazer a ponte disciplinada entre a lógica interna do Odin e o canal externo de execução.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- arquitetura lógica do módulo EXEC;
- contrato técnico da intenção operacional;
- validação pré-execução;
- TTL e expiração;
- controlo de slippage;
- submissão e idempotência;
- classificação do resultado inicial;
- reconciliação e resultado consolidado;
- deteção de divergência;
- persistência mínima executória;
- integração com CORE, RISK, DECISION, MARKET e DASH;
- heartbeat, timeouts, fail-safe e testes técnicos mínimos.

### 2.2 Excluído
Este documento não inclui:
- algoritmo de decisão;
- política de risco em si;
- implementação específica do broker final;
- gestão detalhada de carteira multi-ativo;
- UI detalhada do dashboard.

---

## 3. Objetivos técnicos

O módulo EXEC deverá garantir, no mínimo:

1. **Submissão apenas com intenção formal válida**
   O EXEC não pode agir sem intenção operacional bem formada e ainda válida.

2. **Revalidação imediata**
   O EXEC deve voltar a verificar estado global, risco, mercado e validade temporal imediatamente antes da submissão.

3. **Idempotência**
   O mesmo `intent_id` não pode originar múltiplas submissões cegas.

4. **Slippage controlado**
   O módulo deve respeitar `max_slippage` e diferenciar rejeição preventiva de divergência pós-submissão.

5. **Confirmação antes de assumir sucesso**
   “Submetido” não significa “executado”.

6. **Reconciliação forte**
   O estado executório interno tem de ser alinhado com evidência externa suficiente.

7. **Escalada segura**
   Divergência, ambiguidade e falha crítica devem ser comunicadas ao CORE e ao RECOVERY.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-500 — EXEC
- FSD consolidado v0.5
- SDS-100 — CORE
- SDS-120 — CORE-INTERFACES
- SDS-200 — MARKET
- SDS-400 — RISK
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| Revalidar permissões antes da submissão | FSD-500 | `PreExecutionValidator` |
| Intenção expirada deve gerar evento explícito | FSD-500 / v0.3 | `IntentExpiryGuard` + `EV-INTENTION-EXPIRED` |
| Controlar slippage | FSD-500 / v0.4 | `SlippageGuard` |
| Evitar duplicação cega | FSD-500 | `ExecutionDeduplicator` + `IdempotencyRegistry` |
| Confirmar antes de assumir sucesso | FSD-500 | `ExecutionReconciler` |
| Divergência crítica deve escalar | FSD-500 | `DivergenceDetector` + eventos críticos |

---

## 5. Arquitetura lógica do EXEC

O módulo EXEC deverá ser decomposto, no mínimo, nos seguintes componentes técnicos:

| Componente | Responsabilidade técnica |
|---|---|
| `ExecOrchestrator` | coordenação central do módulo |
| `IntentLoader` | receção e validação básica da intenção |
| `PreExecutionValidator` | validações imediatas antes da submissão |
| `IntentExpiryGuard` | TTL, expiração e janela temporal |
| `SlippageGuard` | controlo de slippage máximo |
| `ExecutionDeduplicator` | prevenção de submissões duplicadas |
| `ExecutionRequestBuilder` | construção do pedido de execução |
| `ExecutionTransportAdapter` | interface abstrata ao canal externo |
| `SubmissionResponseClassifier` | classificação do resultado inicial |
| `ExecutionReconciler` | reconciliação com estado externo |
| `DivergenceDetector` | deteção de divergência crítica |
| `ExecutionStatePublisher` | publicação de estado/eventos |
| `ExecutionSnapshotStore` | persistência mínima executória |
| `ExecAuditLogger` | logging técnico do módulo |
| `ExecHeartbeatEmitter` | heartbeat/liveness do módulo |

---

## 6. Modelo técnico da intenção operacional

### 6.1 Estrutura mínima: `execution_intent`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `intent_id` | Sim | ID único da intenção |
| `decision_cycle_id` | Sim | ID do ciclo decisório |
| `created_at_utc` | Sim | timestamp de criação |
| `ttl_ms` | Sim | tempo de vida da intenção |
| `expires_at_utc` | Sim | timestamp absoluto de expiração |
| `instrument_id` | Sim | instrumento alvo |
| `side` | Sim | buy/sell ou equivalente |
| `target_order_type` | Sim | tipo pretendido |
| `price_reference` | Recomendado | preço-base da intenção |
| `max_slippage` | Sim | slippage máximo aceitável |
| `market_snapshot_ref` | Sim | referência ao estado de mercado |
| `risk_snapshot_ref` | Sim | referência ao estado de risco |
| `decision_version` | Recomendado | versão da lógica/pesos |
| `reason_summary` | Recomendado | racional resumido |
| `restrictions` | Opcional | restrições adicionais |

### 6.2 Regras obrigatórias
- Intenção sem `intent_id` é inválida.
- Intenção sem `expires_at_utc` é inválida.
- Intenção sem `max_slippage` é inválida para fluxo normal.
- Intenção formal não equivale a ordem submetida.

---

## 7. Estados técnicos do EXEC

### 7.1 Estados internos canónicos (`ES-*`)

| Código | Nome técnico | Significado |
|---|---|---|
| ES-10 | WAITING_INTENT | sem intenção válida em processamento |
| ES-20 | INTENT_LOADED | intenção recebida |
| ES-30 | PRECHECK | validação pré-execução em curso |
| ES-40 | READY_TO_SUBMIT | intenção válida e apta à submissão |
| ES-50 | SUBMITTED | pedido enviado |
| ES-60 | PENDING_CONFIRMATION | sem confirmação final suficiente |
| ES-70 | EXECUTION_CONFIRMED | execução confirmada |
| ES-80 | REJECTED | rejeitada antes ou pela submissão |
| ES-90 | FAILED | falha técnica/operacional |
| ES-100 | DIVERGENT | estado externo incompatível |
| ES-110 | CANCELLED_EXPIRED | cancelada ou expirada |

### 7.2 Resultados iniciais (`ER-*`)

| Código | Nome técnico |
|---|---|
| ER-10 | ACCEPTED |
| ER-20 | REJECTED |
| ER-30 | PENDING |
| ER-40 | TECHNICAL_FAILURE |
| ER-50 | AMBIGUOUS |

### 7.3 Resultados consolidados (`EX-*`)

| Código | Nome técnico |
|---|---|
| EX-10 | CONFIRMED_EXECUTED |
| EX-20 | CONFIRMED_REJECTED |
| EX-30 | CONFIRMED_FAILED |
| EX-40 | PENDING_RESOLUTION |
| EX-50 | CRITICAL_DIVERGENCE |
| EX-60 | CANCELLED_EXPIRED |

---

## 8. Entradas técnicas do EXEC

### 8.1 Do DECISION
- `execution_intent` formal;
- `decision_cycle_id`;
- tática selecionada;
- racional resumido.

### 8.2 Do CORE
- `global_state`
- `current_mode`
- `active_block_vector`
- permissões globais
- comandos críticos (`pause`, `stop`, `maintenance`, etc.)

### 8.3 Do RISK
- `risk_decision`
- `risk_state`
- `kill_active`
- cooldown impeditivo;
- restrições adicionais.

### 8.4 Do MARKET
- `market_state`
- `context_state`
- `readiness_state`
- `spread_state`
- `news_guard_active`
- última referência temporal válida.

### 8.5 Do canal externo
- resposta de submissão;
- estado observável da execução;
- erro técnico, quando aplicável.

---

## 9. Validação pré-execução

### 9.1 Objetivo
Garantir que a intenção continua válida no instante imediatamente anterior à submissão.

### 9.2 Verificações mínimas
O `PreExecutionValidator` deverá verificar, no mínimo:
- intenção formal válida;
- `global_state` compatível;
- `current_mode` compatível;
- ausência de kill ativo;
- ausência de bloqueio impeditivo;
- risco não em `BLOCK/KILL`;
- market não incompatível;
- intenção não expirou;
- deduplicação ainda válida;
- integridade mínima do canal de execução.

### 9.3 Regras obrigatórias
- falha em qualquer verificação impeditiva deve impedir submissão;
- verificação deve ser feita o mais perto possível da submissão;
- `READY_TO_SUBMIT` só é válido após este conjunto de checks.

---

## 10. TTL e expiração

### 10.1 Objetivo
Impedir execução tardia baseada em contexto obsoleto.

### 10.2 Regra canónica de expiração
A intenção está expirada se:
- `now_utc > expires_at_utc`; ou
- `now_utc - created_at_utc > ttl_ms`.

### 10.3 Ação obrigatória em expiração
Se a intenção estiver expirada:
1. não submeter;
2. classificar como `ES-110 CANCELLED_EXPIRED`;
3. emitir `EV-INTENTION-EXPIRED`;
4. registar log crítico com diferenças temporais relevantes;
5. publicar o estado ao CORE e ao DASH.

### 10.4 Regras obrigatórias
- expiração não é rejeição genérica;
- expiração repetitiva deve ser observável como problema técnico potencial.

---

## 11. Idempotência e deduplicação

### 11.1 Objetivo
Garantir que o mesmo `intent_id` não provoca múltiplas submissões cegas.

### 11.2 Estrutura mínima de `idempotency_record`

| Campo | Obrigatório |
|---|---|
| `intent_id` | Sim |
| `decision_cycle_id` | Sim |
| `status` | Sim |
| `first_seen_at_utc` | Sim |
| `last_update_at_utc` | Sim |
| `submission_ref` | Opcional |
| `result_state` | Recomendado |

### 11.3 Regras obrigatórias
- `intent_id` repetido com estado final conhecido não pode ser submetido novamente sem fluxo explícito;
- timeout ambíguo não autoriza reenvio cego;
- reenvio, quando existir, deve ser política explícita e auditável.

---

## 12. Construção do pedido de execução

### 12.1 Objetivo
Transformar a intenção validada num pedido técnico para o canal externo.

### 12.2 Estrutura mínima de `execution_request`

| Campo | Obrigatório |
|---|---|
| `request_id` | Sim |
| `intent_id` | Sim |
| `instrument_id` | Sim |
| `side` | Sim |
| `target_order_type` | Sim |
| `price_reference` | Recomendado |
| `max_slippage` | Sim |
| `created_at_utc` | Sim |
| `routing_context` | Recomendado |

### 12.3 Regras obrigatórias
- o pedido deve ser rastreável até à intenção;
- pedido sem `request_id` não deve entrar em submissão normal;
- `max_slippage` deve viajar com o pedido lógico.

---

## 13. Slippage guard

### 13.1 Objetivo
Proteger contra execução fora da tolerância aceitável.

### 13.2 Entradas mínimas
- `price_reference`
- `current_executable_price`, se disponível antes da submissão;
- `max_slippage`

### 13.3 Modos de atuação

#### 13.3.1 Rejeição preventiva
Se antes da submissão:
- o preço executável conhecido já exceder `max_slippage`

então o EXEC deverá:
- rejeitar a intenção;
- emitir `EV-EXEC-REJECTED-SLIPPAGE`;
- não submeter.

#### 13.3.2 Divergência pós-submissão
Se após submissão:
- o preço confirmado exceder `max_slippage`

então o EXEC deverá:
- classificar o caso como divergente ou fora da tolerância;
- publicar evento crítico;
- informar CORE, RISK e DASH.

### 13.4 Regras obrigatórias
- slippage excessivo não pode ser tratado como execução normal;
- ausência de dado de preço suficiente deve levar a política conservadora, não a assunção otimista.

---

## 14. Submissão ao canal externo

### 14.1 Objetivo
Enviar o pedido de execução ao adaptador de transporte.

### 14.2 Requisitos técnicos
O `ExecutionTransportAdapter` deverá:
- encapsular o protocolo externo;
- devolver resposta inicial padronizada;
- distinguir falha técnica de rejeição semântica;
- preservar `request_id` / `intent_id` para correlação.

### 14.3 Regras obrigatórias
- o EXEC não deve ficar acoplado semanticamente ao broker final;
- o adaptador deve ser abstraído e mockável para testes.

---

## 15. Classificação do resultado inicial

### 15.1 Objetivo
Classificar a resposta imediata do canal externo.

### 15.2 Regras mínimas

#### `ER-10 ACCEPTED`
Canal aceitou o pedido, mas isso não implica confirmação final.

#### `ER-20 REJECTED`
Pedido recusado explicitamente.

#### `ER-30 PENDING`
Pedido aceite/enviado, mas sem estado final confiável.

#### `ER-40 TECHNICAL_FAILURE`
Erro de transporte, serialização ou indisponibilidade.

#### `ER-50 AMBIGUOUS`
Não é possível afirmar com confiança suficiente o estado inicial.

### 15.3 Regra obrigatória
`ACCEPTED` não deve ser promovido diretamente a `CONFIRMED_EXECUTED` sem reconciliação suficiente.

---

## 16. Reconciliação

### 16.1 Objetivo
Determinar o estado executório real e alinhar o estado interno com a evidência externa.

### 16.2 Entradas mínimas
- `execution_request`
- resultado inicial
- resposta/observação externa
- contexto temporal
- eventual estado de posição/ordem devolvido pela fonte externa

### 16.3 Resultado mínimo
A reconciliação deverá convergir para um `EX-*` canónico.

### 16.4 Regras obrigatórias
- ausência de confirmação não é confirmação positiva;
- reconciliação falhada deve manter pendência ou divergência;
- reconciliação deve preservar rastreabilidade por `intent_id` e `request_id`.

---

## 17. Deteção de divergência

### 17.1 Objetivo
Sinalizar incompatibilidade entre estado esperado e estado observado.

### 17.2 Cenários mínimos
- intenção dada como não executada mas com evidência externa de execução;
- intenção dada como executada sem evidência compatível;
- duplicação inesperada;
- slippage confirmado fora da tolerância;
- resposta ambígua persistente;
- pedido pendente sem fecho além da janela suportada.

### 17.3 Regra obrigatória
Divergência crítica deve:
- gerar `EV-EXEC-DIVERGENCE`;
- mover o EXEC para `ES-100 DIVERGENT`;
- informar CORE, RISK, DASH;
- permitir escalada a RECOVERY.

---

## 18. Persistência mínima do EXEC

### 18.1 Objetivo
Preservar memória mínima executória para reconciliação e recovery.

### 18.2 Itens mínimos a persistir
- `idempotency_record`
- última intenção em processamento;
- último resultado inicial;
- último resultado consolidado;
- última divergência relevante;
- timestamps críticos do ciclo executório.

### 18.3 Estrutura mínima: `execution_snapshot`

| Campo | Obrigatório |
|---|---|
| `execution_snapshot_id` | Sim |
| `intent_id` | Sim |
| `request_id` | Opcional |
| `exec_state` | Sim |
| `initial_result` | Opcional |
| `final_result` | Opcional |
| `created_at_utc` | Sim |
| `updated_at_utc` | Sim |
| `divergence_flag` | Sim |
| `reason_summary` | Recomendado |

### 18.4 Regras obrigatórias
- persistência executória não substitui a persistência do CORE;
- divergência e pendência relevante devem sobreviver a restart para recovery.

---

## 19. Eventos publicados pelo EXEC

### 19.1 Eventos mínimos
- `EV-EXEC-SUBMITTED`
- `EV-EXEC-CONFIRMED`
- `EV-EXEC-REJECTED`
- `EV-EXEC-REJECTED-SLIPPAGE`
- `EV-INTENTION-EXPIRED`
- `EV-EXEC-DIVERGENCE`
- `EV-HB-OK`

### 19.2 Regras obrigatórias
- eventos devem ser emitidos apenas quando houver mudança material de estado;
- divergência e expiração devem ser explicitamente diferenciadas.

---

## 20. Interface com CORE

### 20.1 O CORE consome do EXEC
- `exec_state`
- eventos executórios críticos;
- divergência;
- intenção expirada;
- heartbeat.

### 20.2 Payload mínimo publicado ao CORE

| Campo | Obrigatório |
|---|---|
| `exec_state` | Sim |
| `intent_id` | Recomendado |
| `request_id` | Recomendado |
| `initial_result` | Opcional |
| `final_result` | Opcional |
| `divergence_flag` | Sim |
| `reason_summary` | Recomendado |

### 20.3 Regras obrigatórias
- o CORE deve poder decidir bloqueio/recovery sem recalcular lógica executória interna;
- divergência crítica tem de ser suficientemente explícita para o CORE.

---

## 21. Interface com RISK

### 21.1 O EXEC consome do RISK
- `risk_decision`
- `risk_state`
- kill ativo;
- cooldown impeditivo;
- restrições adicionais.

### 21.2 O RISK consome do EXEC
- resultado relevante;
- slippage excessivo;
- divergência;
- efeitos que alterem o envelope.

### 21.3 Regras obrigatórias
- o EXEC não deve submeter se o RISK estiver em `BLOCK` ou `KILL`;
- o RISK deve ser atualizado rapidamente quando eventos executórios alterem o perfil de risco.

---

## 22. Interface com MARKET

### 22.1 O EXEC consome do MARKET
- `market_state`
- `context_state`
- `readiness_state`
- `spread_state`
- `news_guard_active`
- última atualização válida.

### 22.2 Regras obrigatórias
- o EXEC deve impedir submissão se o MARKET se tornar incompatível no precheck;
- market degradado/hostil pode invalidar a intenção antes da submissão.

---

## 23. Interface com DECISION

### 23.1 O EXEC consome do DECISION
- intenção formal;
- racional resumido;
- tática selecionada;
- `decision_cycle_id`.

### 23.2 Regras obrigatórias
- sem intenção formal não existe submissão;
- o EXEC não reinterpreta a tática, apenas valida exequibilidade técnica.

---

## 24. Interface com DASH

### 24.1 O DASH consome do EXEC
- estado executório;
- submissão recente;
- resultado inicial;
- resultado consolidado;
- expiração;
- divergência.

### 24.2 Regras obrigatórias
- o DASH deve distinguir:
  - submetido
  - aceite
  - executado confirmado
  - expirado
  - rejeitado
  - divergente

---

## 25. Heartbeat do EXEC

### 25.1 Objetivo
Permitir ao CORE saber se o módulo EXEC está vivo e funcional.

### 25.2 Payload mínimo do heartbeat

| Campo | Obrigatório |
|---|---|
| `module_id` | Sim |
| `timestamp_utc` | Sim |
| `exec_state` | Sim |
| `last_intent_id` | Opcional |
| `health_flag` | Sim |
| `pending_count` | Recomendado |

### 25.3 Regras obrigatórias
- heartbeat deve ser periódico e parametrizável;
- EXEC vivo mas preso em pendência prolongada deve refletir degradação do `health_flag`.

---

## 26. Logging técnico do EXEC

### 26.1 Campos mínimos
- `timestamp_utc`
- `intent_id`
- `request_id`
- `exec_state`
- `initial_result`
- `final_result`
- `slippage_value`
- `divergence_flag`
- `severity`
- `message`

### 26.2 Eventos obrigatórios a logar
- receção da intenção;
- falha de precheck;
- expiração;
- rejeição por slippage;
- submissão;
- resposta inicial;
- confirmação final;
- pendência prolongada;
- divergência crítica;
- mudança relevante de estado interno.

---

## 27. Timeouts e fail-safe

### 27.1 Timeouts mínimos parametrizáveis

| Parâmetro | Função |
|---|---|
| `exec_precheck_timeout_ms` | timeout do precheck |
| `exec_submission_timeout_ms` | timeout de submissão |
| `exec_confirmation_timeout_ms` | timeout para confirmação suficiente |
| `exec_pending_resolution_timeout_ms` | pendência máxima tolerada |
| `exec_heartbeat_interval_ms` | intervalo de heartbeat |
| `exec_heartbeat_timeout_ms` | timeout de liveness |

### 27.2 Regras obrigatórias
- timeout no precheck deve impedir submissão;
- timeout de confirmação não pode ser tratado como execução confirmada;
- pendência acima do limite deve poder escalar para divergência/recovery;
- silêncio do EXEC em contexto crítico deve levar o CORE a estado seguro.

---

## 28. Erros de contrato e erro interno

### 28.1 Tipos mínimos
- `exec_invalid_intent`
- `exec_missing_required_field`
- `exec_schema_version_mismatch`
- `exec_precheck_failed`
- `exec_transport_failure`
- `exec_reconciliation_failure`
- `exec_idempotency_conflict`

### 28.2 Regras obrigatórias
- intenção inválida não deve entrar no pipeline normal;
- conflito de idempotência deve ser tratado como evento técnico sério;
- falha interna recorrente deve ser observável e escalável.

---

## 29. Testes técnicos mínimos

### 29.1 Unit tests
- validade de TTL/expiração;
- rejeição por slippage;
- idempotência por `intent_id`;
- classificação `ER-*`;
- classificação `EX-*`;
- deteção de divergência.

### 29.2 Integration tests
- intenção válida e execução confirmada;
- intenção expirada antes de submissão;
- slippage preventivo acima do limite;
- rejeição técnica na submissão;
- pendência seguida de confirmação;
- pendência seguida de divergência;
- bloqueio por RISK antes do submit;
- invalidação por MARKET no precheck.

### 29.3 Fault-injection tests
- timeout do canal externo;
- resposta inicial ambígua;
- confirmação externa contraditória;
- reenvio acidental do mesmo `intent_id`;
- perda de heartbeat durante pendência crítica.

---

## 30. Critérios de aceitação

O SDS-500 — EXEC será considerado tecnicamente suficiente quando:

1. a arquitetura do módulo suportar receção, validação e submissão controlada da intenção;
2. TTL, expiração e slippage estiverem tecnicamente definidos;
3. a idempotência estiver formalizada;
4. o módulo conseguir distinguir resultado inicial e resultado consolidado;
5. divergência crítica estiver formalizada com escalada adequada;
6. o EXEC puder integrar-se com CORE, RISK, MARKET, DECISION e DASH sem ambiguidade;
7. o documento permitir implementação e testes diretos.

---

## 31. Dependências e próximos documentos

### 31.1 Dependências principais
- SDS-100 — CORE
- SDS-120 — CORE-INTERFACES
- SDS-200 — MARKET
- SDS-400 — RISK
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 31.2 Próximos documentos recomendados
1. **SDS-300 — DECISION**
2. **SDS-600 — DASH**
3. **SDS-700 — RECOVERY**
4. **SDS-800 — LEARN**

---

## 32. Conclusão

O SDS-500 transforma a execução do Odin num componente técnico controlado, rastreável e auditável.

Sem este documento, o sistema arrisca-se a decidir bem e executar mal: tarde, duplicado, fora da tolerância, sem confirmação ou em divergência silenciosa.

Com este documento, o EXEC passa a ter:
- contrato formal da intenção;
- guardas de validade e slippage;
- idempotência;
- reconciliação explícita;
- escalada técnica de divergência.

Num sistema deste tipo, a execução é onde a teoria encontra o custo real. E é aí que a engenharia tem de ser menos permissiva.
