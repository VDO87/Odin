# SDS-300 — DECISION
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Arquitetura técnica do motor de decisão, avaliação de táticas, scoring, filtros, seleção de hipótese, emissão da intenção operacional e integração com CORE, MARKET, RISK e EXEC.

---

## 1. Finalidade do documento

Este documento define a especificação técnica do módulo **DECISION** do Odin.

Se o FSD-300 define **o que** o módulo DECISION deve fazer, este SDS-300 define **como** o motor decisório deve ser estruturado para:
- consumir contexto válido;
- avaliar táticas configuradas;
- filtrar hipóteses inelegíveis;
- calcular scoring auditável;
- selecionar uma hipótese prioritária;
- emitir uma intenção operacional formal e temporalmente válida;
- evitar decisões inconsistentes, opacas ou obsoletas.

O DECISION é o ponto onde o Odin deixa de ser apenas observador e passa a propor ação concreta. Por isso, a sua implementação tem de ser determinística, explicável e fortemente integrada com CORE, MARKET, RISK e EXEC.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- arquitetura lógica do motor DECISION;
- pipeline técnico do ciclo decisório;
- contratos de entrada e saída;
- estrutura técnica de táticas e hipóteses;
- elegibilidade, scoring e ranking;
- emissão de intenção operacional;
- regras de validade temporal da intenção;
- gestão de racional técnico da decisão;
- tratamento de bloqueios externos;
- integração com MARKET, CORE, RISK, EXEC, DASH e LEARN;
- requisitos mínimos de observabilidade e testes.

### 2.2 Excluído
Este documento não inclui:
- desenho matemático final de cada estratégia de trading;
- implementação broker-specific;
- detalhe do dashboard;
- persistência profunda do histórico de aprendizagem;
- otimização estatística avançada do LEARN.

---

## 3. Objetivos técnicos

O módulo DECISION deverá garantir, no mínimo:

1. **Determinismo por ciclo**  
   O mesmo conjunto de inputs válidos, na mesma versão de lógica e pesos, deve produzir a mesma saída.

2. **Separação clara entre elegibilidade e scoring**  
   Hipóteses não elegíveis não devem entrar no ranking como se fossem candidatas válidas.

3. **Explicabilidade técnica**  
   A decisão final deve poder ser decomposta em:
   - hipóteses avaliadas;
   - filtros aplicados;
   - fatores de scoring;
   - motivo de seleção ou rejeição.

4. **Validade temporal da intenção**  
   Toda intenção emitida deve ser curta, explícita e rejeitável se expirar.

5. **Integração forte com bloqueios externos**  
   O DECISION não pode emitir intenção executável normal se CORE, MARKET ou RISK publicarem estado incompatível.

6. **Segurança contra race conditions lógicas**  
   O motor deve evitar emitir intenções obsoletas ou múltiplas intenções concorrentes para o mesmo ciclo sem política explícita.

7. **Uso auditável de memória auxiliar**  
   Se contexto histórico auxiliar for usado no ciclo, ele deve ser advisory, congelado no snapshot e reconstruível no racional.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-300 — DECISION
- FSD consolidado v0.5
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX
- SDS-100 — CORE
- SDS-200 — MARKET
- SDS-400 — RISK
- SDS-500 — EXEC

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| O sistema deve avaliar táticas configuradas | FSD-300 | `TacticRegistry` + `TacticEvaluator` |
| O sistema deve distinguir elegibilidade de scoring | FSD-300 | `EligibilityEngine` + `ScoringEngine` |
| O sistema deve produzir uma saída única por ciclo | FSD-300 | `DecisionCycleRunner` + `DecisionSelector` |
| A intenção operacional deve ter TTL e expiração | FSD-300 / v0.2+ | `IntentBuilder` + `IntentTTLPolicy` |
| A decisão deve respeitar bloqueios externos | FSD-300 / CORE/RISK/MARKET | `ExecutionWindowGuard` |
| A decisão deve ser auditável | FSD-300 | `DecisionRationaleBuilder` + `DecisionAuditLogger` |

---

## 5. Arquitetura lógica do DECISION

O DECISION deverá ser decomposto, no mínimo, nos seguintes componentes técnicos.

### 5.1 Componentes principais

| Componente | Responsabilidade técnica |
|---|---|
| `DecisionEngine` | orquestra o ciclo decisório |
| `DecisionCycleRunner` | executa o pipeline completo por ciclo |
| `InputSnapshotBuilder` | congela inputs coerentes do ciclo |
| `ExecutionWindowGuard` | valida se o ciclo pode prosseguir |
| `TacticRegistry` | regista e expõe táticas ativas |
| `EligibilityEngine` | filtra hipóteses inelegíveis |
| `TacticEvaluator` | avalia sinais por tática |
| `ScoringEngine` | calcula score por hipótese elegível |
| `ConfluenceEvaluator` | mede confluências e reforços/penalizações |
| `DecisionSelector` | ordena, desempata e seleciona a hipótese final |
| `MemoryAdvisoryRetriever` | recupera contexto histórico auxiliar não autoritativo |
| `IntentBuilder` | constrói a intenção operacional |
| `IntentTTLPolicy` | define TTL, expiração e validade temporal |
| `DecisionRationaleBuilder` | monta racional técnico auditável |
| `DecisionStatePublisher` | publica estado resumido do módulo |
| `DecisionAuditLogger` | logging estruturado do ciclo |

---

## 6. Modelo técnico do ciclo decisório

### 6.1 Fases mínimas do ciclo

Todo ciclo decisório deverá seguir, no mínimo, as seguintes fases:

1. **captura de snapshot de inputs**
2. **validação de janela de decisão**
3. **carregamento das táticas ativas**
4. **avaliação de elegibilidade**
5. **avaliação técnica por tática**
6. **cálculo de score**
7. **ranking das hipóteses**
8. **seleção da hipótese prioritária**
9. **construção da decisão final**
10. **emissão de intenção, se aplicável**
11. **publicação do racional e logging**

### 6.2 Regra obrigatória
O ciclo deve operar sobre um **snapshot coerente** dos inputs, e não sobre leituras soltas que mudam a meio da avaliação.

---

## 7. Snapshot técnico de entrada

### 7.1 Objetivo
Congelar uma fotografia consistente do estado necessário ao ciclo.

### 7.2 Estrutura mínima: `decision_input_snapshot`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `snapshot_id` | Sim | ID único do snapshot |
| `created_at_utc` | Sim | timestamp do snapshot |
| `global_state` | Sim | estado global vindo do CORE |
| `current_mode` | Sim | modo vindo do CORE |
| `market_state` | Sim | estado resumido do MARKET |
| `context_class` | Sim | classe de contexto resumido |
| `feed_integrity_state` | Sim | integridade do feed |
| `risk_state` | Sim | allow/restrict/block/kill |
| `kill_active` | Sim | kill ativo ou não |
| `active_block_vector_summary` | Sim | resumo dos bloqueios ativos |
| `instrument_snapshot_ref` | Sim | referência aos dados de mercado usados |
| `decision_config_version` | Sim | versão da lógica/pesos ativos |
| `memory_advisory_context_ref` | Não | referência ao contexto histórico auxiliar usado |
| `memory_advisory_hash` | Não | hash do conjunto advisory congelado |

### 7.3 Regras obrigatórias
- O snapshot deve ser imutável durante o ciclo.
- O snapshot deve ser identificável e correlacionável com a intenção final.
- O DECISION não deve usar inputs “mais novos” a meio do mesmo ciclo sem reiniciar o ciclo.
- Se memória auxiliar for usada, os resultados efetivamente considerados devem ser congelados neste snapshot.

---

## 8. Guard de janela de decisão

### 8.1 Objetivo
Impedir o arranque do ciclo quando o contexto global não é compatível.

### 8.2 Regras mínimas do `ExecutionWindowGuard`
O ciclo só pode prosseguir se:
- `global_state` for compatível com decisão;
- `current_mode` permitir avaliação operacional;
- `kill_active` for falso;
- não existir bloqueio dominante impeditivo;
- `market_state` não estiver em estado incompatível;
- `risk_state` não estiver em block/kill.

### 8.3 Saídas possíveis
- `WINDOW_OPEN`
- `WINDOW_RESTRICTED`
- `WINDOW_BLOCKED`

### 8.4 Regra obrigatória
`WINDOW_BLOCKED` impede emissão de intenção operacional normal.

---

## 9. Modelo técnico de tática

### 9.1 Estrutura mínima: `tactic_definition`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `tactic_id` | Sim | ID único da tática |
| `name` | Sim | nome lógico |
| `is_active` | Sim | ativa/inativa |
| `priority_base` | Recomendado | prioridade base |
| `eligibility_rules_ref` | Sim | referência às regras mínimas |
| `scoring_profile_ref` | Sim | referência ao perfil de scoring |
| `min_score_threshold` | Sim | score mínimo |
| `confluence_policy_ref` | Recomendado | política de confluência |
| `allowed_modes` | Sim | modos em que pode concorrer |
| `cooldown_policy_ref` | Opcional | política de arrefecimento |

### 9.2 Regra obrigatória
Táticas sem regras mínimas ou sem `min_score_threshold` não devem ser carregadas como candidatas válidas.

---

## 10. Modelo técnico de hipótese

### 10.1 Estrutura mínima: `candidate_hypothesis`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `hypothesis_id` | Sim | ID único da hipótese |
| `decision_cycle_id` | Sim | ciclo a que pertence |
| `tactic_id` | Sim | tática de origem |
| `instrument_ref` | Sim | instrumento/ativo alvo |
| `direction` | Recomendado | direção da hipótese |
| `is_eligible` | Sim | elegível ou não |
| `eligibility_fail_reasons` | Não | motivos de inelegibilidade |
| `base_signal_state` | Sim | estado do sinal base |
| `confluence_summary` | Recomendado | resumo de confluências |
| `score_value` | Não | score final se elegível |
| `score_breakdown_ref` | Não | referência ao detalhe do score |
| `ranking_position` | Não | posição no ranking final |

### 10.2 Regras obrigatórias
- Hipóteses inelegíveis não devem ter `score_value` operacional normal.
- Hipóteses elegíveis mas fracas devem ser distinguíveis das inelegíveis.
- O ranking só inclui hipóteses elegíveis.

---

## 11. Elegibilidade técnica

### 11.1 Objetivo
Separar as hipóteses que podem competir daquelas que devem ser eliminadas imediatamente.

### 11.2 Entradas mínimas do `EligibilityEngine`
- snapshot do CORE;
- snapshot do MARKET;
- estado do RISK;
- regras da tática;
- contexto temporal;
- cooldown da tática, quando aplicável.

### 11.3 Critérios mínimos de elegibilidade
- modo permitido;
- estado global compatível;
- mercado não inválido para a tática;
- risco não bloqueante;
- integridade mínima do feed;
- regras próprias da tática satisfeitas.

### 11.4 Saídas mínimas
- `ELIGIBLE`
- `NOT_ELIGIBLE_EXTERNAL`
- `NOT_ELIGIBLE_TACTIC_RULE`
- `NOT_ELIGIBLE_CONTEXT`

### 11.5 Regra obrigatória
Os motivos de inelegibilidade devem ser preservados para racional e auditoria.

---

## 12. Scoring técnico

### 12.1 Objetivo
Atribuir valor comparável às hipóteses elegíveis.

### 12.2 Estrutura mínima: `score_result`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `hypothesis_id` | Sim | hipótese alvo |
| `score_value` | Sim | valor final |
| `score_components` | Sim | componentes do score |
| `positive_factors` | Recomendado | fatores positivos |
| `negative_factors` | Recomendado | fatores negativos |
| `penalties_applied` | Recomendado | penalizações |
| `calculated_at_utc` | Sim | timestamp |
| `scoring_profile_version` | Sim | versão do perfil |

### 12.3 Componentes técnicos mínimos
O `ScoringEngine` deverá conseguir incorporar, no mínimo:
- qualidade do sinal base;
- adequação ao contexto;
- confluências;
- adequação à sessão;
- penalização por mercado sensível/hostil;
- prioridade base da tática.

### 12.4 Regras obrigatórias
- o score deve ser reprodutível para o mesmo snapshot e versão;
- o score deve ser auditável por componentes;
- scores abaixo de `min_score_threshold` não devem ser promovidos a intenção.

---

## 13. Confluência técnica

### 13.1 Objetivo
Evitar decisões baseadas num único gatilho fraco.

### 13.2 Estrutura mínima: `confluence_result`

| Campo | Obrigatório |
|---|---|
| `hypothesis_id` | Sim |
| `confluence_count` | Sim |
| `confluence_quality_score` | Recomendado |
| `required_confluence_met` | Sim |
| `confluence_flags` | Recomendado |

### 13.3 Regra obrigatória
Se a política da tática exigir confluência mínima e esta falhar, a hipótese deve ser:
- inelegível; ou
- fortemente penalizada, conforme a política definida.

---

## 14. Seleção e desempate

### 14.1 Objetivo
Escolher uma única saída principal do ciclo.

### 14.2 Responsabilidade do `DecisionSelector`
- ordenar hipóteses elegíveis;
- aplicar desempate;
- selecionar a hipótese vencedora;
- determinar se a melhor hipótese ainda assim não é suficiente para operação.

### 14.3 Regras mínimas de desempate
Ordem recomendada:
1. maior `score_value`
2. maior `confluence_quality_score`
3. maior `priority_base`
4. política configurada por tática
5. não operar, se persistir empate não resolvido

### 14.4 Regra obrigatória
Sem política explícita de multi-intenção, o ciclo só pode produzir **uma** hipótese vencedora.

---

## 15. Saída técnica do ciclo

### 15.1 Estrutura mínima: `decision_cycle_result`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `decision_cycle_id` | Sim | ID único do ciclo |
| `snapshot_id` | Sim | snapshot de entrada |
| `decision_state` | Sim | estado final do módulo |
| `decision_output` | Sim | saída formal do ciclo |
| `winner_hypothesis_id` | Não | hipótese escolhida |
| `intent_emitted` | Sim | booleano |
| `blocked_by_external` | Sim | booleano |
| `reason_summary` | Sim | motivo principal |
| `generated_at_utc` | Sim | timestamp final |

### 15.2 Valores mínimos de `decision_output`
- `NO_ACTION`
- `WAIT`
- `CANDIDATE_SELECTED`
- `RESTRICTED`
- `BLOCKED`
- `ERROR`

---

## 16. Intenção operacional técnica

### 16.1 Objetivo
Formalizar a proposta de ação que poderá ser consumida pelo EXEC.

### 16.2 Estrutura mínima: `operational_intent`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `intent_id` | Sim | ID único da intenção |
| `decision_cycle_id` | Sim | ciclo de origem |
| `hypothesis_id` | Sim | hipótese vencedora |
| `tactic_id` | Sim | tática selecionada |
| `created_at_utc` | Sim | criação da intenção |
| `ttl_ms` | Sim | tempo de vida |
| `expires_at_utc` | Sim | timestamp de expiração |
| `market_snapshot_ref` | Sim | referência ao snapshot de mercado |
| `risk_snapshot_ref` | Sim | referência ao snapshot de risco |
| `decision_config_version` | Sim | versão da lógica/pesos |
| `max_slippage` | Sim | slippage máximo permitido |
| `intent_direction` | Recomendado | direção |
| `restriction_flags` | Recomendado | flags de restrição relevantes |
| `rationale_ref` | Recomendado | referência ao racional técnico |
| `memory_advisory_context_ref` | Recomendado | referência ao contexto advisory congelado |

### 16.3 Regras obrigatórias
- toda intenção deve ser única por `intent_id`;
- `expires_at_utc` deve ser derivado de `created_at_utc + ttl_ms`;
- intenção sem `ttl_ms` ou `expires_at_utc` é inválida;
- o DECISION não assume execução; apenas emite intenção;
- intenção emitida sobre snapshot antigo não deve ser reciclada.

---

## 17. Política técnica de TTL

### 17.1 Objetivo
Evitar execução tardia baseada em contexto envelhecido.

### 17.2 Regras mínimas
A `IntentTTLPolicy` deverá definir:
- TTL por modo;
- TTL por classe de tática, se necessário;
- TTL máximo absoluto do sistema.

### 17.3 Regra obrigatória
O TTL deve ser curto e compatível com o ritmo do mercado e da execução.

### 17.4 Interação com EXEC
Se `now > expires_at_utc`, o EXEC deverá gerar:
- `EV-INTENTION-EXPIRED`

O DECISION deve considerar este evento como feedback operacional relevante, mas não como falha automática do modelo decisório.

---

## 18. Racional técnico da decisão

### 18.1 Objetivo
Gerar explicação auditável, não apenas um score.

### 18.2 Estrutura mínima: `decision_rationale`

| Campo | Obrigatório |
|---|---|
| `decision_cycle_id` | Sim |
| `winner_hypothesis_id` | Não |
| `top_positive_factors` | Sim |
| `top_negative_factors` | Sim |
| `eligibility_rejections_summary` | Recomendado |
| `external_block_summary` | Recomendado |
| `score_breakdown_refs` | Recomendado |
| `final_reason_text` | Sim |

### 18.3 Regra obrigatória
O racional deve distinguir claramente:
- sem oportunidade;
- oportunidade fraca;
- oportunidade válida mas bloqueada externamente;
- erro no próprio ciclo.

---

## 19. Estados internos do DECISION

### 19.1 Estados canónicos recomendados

| Código | Nome |
|---|---|
| DS-10 | WAITING_INPUTS |
| DS-20 | READY_TO_EVALUATE |
| DS-30 | EVALUATING |
| DS-40 | NO_VALID_OPPORTUNITY |
| DS-50 | OPPORTUNITY_SELECTED |
| DS-60 | BLOCKED_EXTERNALLY |
| DS-70 | INTENT_EMITTED |
| DS-80 | DECISION_ERROR |

### 19.2 Regra obrigatória
O estado interno publicado pelo DECISION deve ser compatível com `decision_output`.

---

## 20. Interfaces técnicas

### 20.1 Interface com CORE
O DECISION deve consumir do CORE:
- `global_state`
- `current_mode`
- `dominant_block_reason`
- `active_block_vector_summary`
- `available_execution_window` ou equivalente
- `critical_flags`

O DECISION deve publicar ao CORE, no mínimo:
- `decision_state`
- `decision_cycle_id`
- `decision_output`
- `blocked_by_external`
- `reason_summary`
- heartbeat (se configurado)

### 20.2 Interface com MARKET
O DECISION deve consumir do MARKET:
- `market_state`
- `context_class`
- `feed_integrity_state`
- `session_ref`
- `instrument_snapshot_ref`
- `news_guard_state` (quando aplicável)

### 20.3 Interface com RISK
O DECISION deve consumir do RISK:
- `risk_state`
- `kill_active`
- `risk_snapshot_ref`
- `restriction_flags`
- `cooldown_state` (quando aplicável)

### 20.4 Interface com EXEC
O DECISION publica ao EXEC:
- `operational_intent`

O feedback do EXEC relevante para o DECISION pode incluir:
- `EV-INTENTION-EXPIRED`
- `EV-EXEC-REJECTED-SLIPPAGE`
- estados resumidos de execução relevantes para analytics futuros

### 20.5 Interface com DASH
O DECISION deve publicar ao DASH, no mínimo:
- `decision_state`
- `decision_output`
- `winner_hypothesis_summary`
- `score_summary`
- `reason_summary`
- `blocked_by_external`

### 20.6 Interface com LEARN
O DECISION deve expor ao LEARN:
- score histórico por tática;
- eficácia por tática;
- racional resumido;
- versão de configuração usada no ciclo.

### 20.7 Interface com memória auxiliar
O DECISION pode consumir de uma camada de memória auxiliar, como MemPalace:
- contexto histórico por tática;
- incidentes ou divergências semanticamente próximos;
- racional técnico de ciclos anteriores;
- resultados de testes ou shadow sessions relevantes.

Regras obrigatórias:
- esta interface é opcional e advisory;
- falha desta interface não pode promover decisão mais arriscada;
- resultados usados devem ser congelados no `decision_input_snapshot`;
- o racional deve indicar quando houve influência de memória auxiliar.

---

## 21. Concorrência e serialização

### 21.1 Princípio base
O DECISION deve evitar múltiplos ciclos concorrentes sobre o mesmo contexto lógico sem política explícita.

### 21.2 Estratégia recomendada
- um `DecisionCycleRunner` principal por contexto/instrumento;
- fila sequencial ou actor por domínio de decisão;
- `InputSnapshotBuilder` executado antes da avaliação;
- invalidar ou descartar ciclos antigos quando chega contexto mais recente, conforme política.

### 21.3 Regra obrigatória
O módulo não deve emitir duas intenções ativas equivalentes para o mesmo domínio sem estratégia explícita e auditável.

---

## 22. Regras de falha

### 22.1 Falhas mínimas a tratar
- snapshot de entrada incompleto;
- tática mal configurada;
- erro no scoring;
- erro na construção da intenção;
- incompatibilidade entre `decision_output` e `decision_state`;
- versão de configuração não carregável.

### 22.2 Fallback
O fallback preferencial do DECISION é:
- `decision_output = ERROR` ou `BLOCKED`
- nenhuma intenção emitida
- log crítico estruturado

### 22.3 Regra obrigatória
Em caso de erro decisório, o módulo não deve fabricar uma intenção “por defeito”.

---

## 23. Observabilidade e logging técnico

### 23.1 Eventos mínimos a registar
- início do ciclo;
- snapshot criado;
- táticas carregadas;
- hipóteses inelegíveis com motivo;
- scores calculados;
- hipótese vencedora;
- decisão final;
- intenção emitida;
- ciclo bloqueado externamente;
- erro decisório.

### 23.2 Campos mínimos de log
- `decision_cycle_id`
- `snapshot_id`
- `tactic_id` / `hypothesis_id` quando aplicável
- `decision_state`
- `decision_output`
- `score_value` quando aplicável
- `reason_summary`
- `timestamp_utc`
- `severity`

### 23.3 Regra obrigatória
O logging do DECISION deve permitir reconstruir o ciclo sem depender apenas do código.

---

## 24. Estrutura técnica recomendada de código

```text
odin/
├── src/
│   ├── decision/
│   │   ├── engine/
│   │   ├── cycle_runner/
│   │   ├── input_snapshot/
│   │   ├── tactics/
│   │   ├── eligibility/
│   │   ├── scoring/
│   │   ├── confluence/
│   │   ├── selector/
│   │   ├── intent/
│   │   ├── rationale/
│   │   ├── publisher/
│   │   └── audit/
│   ├── shared/
│   │   ├── models/
│   │   ├── enums/
│   │   ├── logging/
│   │   └── utils/
│   └── config/
```

---

## 25. Testes técnicos mínimos

### 25.1 Unit tests
- elegibilidade por tática;
- cálculo de score;
- aplicação de penalizações;
- desempate;
- construção da intenção;
- cálculo de `expires_at_utc`;
- racional técnico.

### 25.2 Integration tests
- ciclo sem oportunidade válida;
- ciclo com oportunidade em demo;
- ciclo com bloqueio externo por RISK;
- ciclo com mercado hostil;
- emissão de intenção válida;
- intenção rejeitada por expiração no EXEC;
- intenção com `max_slippage` encaminhada corretamente.

### 25.3 Determinism tests
- mesmos inputs + mesma versão -> mesma decisão;
- snapshot imutável durante o ciclo;
- ausência de múltiplas intenções equivalentes no mesmo ciclo.

---

## 26. Critérios de aceitação

O SDS-300 — DECISION será considerado tecnicamente suficiente quando:

1. o ciclo decisório puder ser implementado sem ambiguidades graves;
2. elegibilidade, scoring e seleção estiverem claramente separados;
3. a intenção operacional tiver contrato técnico completo;
4. o TTL da intenção estiver definido e rastreável;
5. o racional puder ser reconstruído tecnicamente;
6. o módulo respeitar bloqueios externos;
7. o módulo não emitir intenções inválidas por falha interna;
8. a arquitetura permitir testes determinísticos e integração com EXEC.

---

## 27. Dependências e próximos documentos

### 27.1 Dependências principais
- SDS-100 — CORE
- SDS-200 — MARKET
- SDS-400 — RISK
- SDS-500 — EXEC
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 27.2 Próximos documentos recomendados
1. **SDS-600 — DASH**
2. **SDS-700 — RECOVERY**
3. **SDS-800 — LEARN**

---

## 28. Conclusão

O SDS-300 transforma o motor de decisão do Odin numa peça tecnicamente implementável, auditável e controlável.

Sem esta camada, o sistema poderia ter market, risk e exec bem desenhados, mas o elo central entre observar e agir continuaria difuso. Com este documento, o DECISION passa a ter:
- pipeline claro;
- contrato formal de intenção;
- separação limpa entre filtros, score e seleção;
- racional técnico reconstruível;
- integração segura com o resto do sistema.

Num sistema destes, decidir não é apenas “ter uma estratégia”. É ter um motor disciplinado que sabe quando não deve agir.
