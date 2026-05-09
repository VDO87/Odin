# SDS-800 — LEARN
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Arquitetura técnica do módulo LEARN, análise de histórico, geração de propostas, snapshots, shadow mode, ativação controlada, rollback e governação da evolução funcional.

---

## 1. Finalidade do documento

Este documento define a especificação técnica do módulo **LEARN** do Odin.

Se o FSD-800 define **o que** o módulo de aprendizagem deve fazer, este SDS-800 define **como** a evolução controlada do sistema deve ser estruturada tecnicamente para:

- recolher e consolidar histórico relevante;
- avaliar desempenho por tática, contexto e versão;
- gerar propostas de alteração rastreáveis;
- criar snapshots antes de qualquer mudança relevante;
- testar versões candidatas em shadow mode;
- promover versões sob critérios explícitos;
- reverter com segurança quando a nova versão degrada;
- impedir alterações destrutivas, opacas ou não auditáveis.

O LEARN não existe para “mudar coisas porque sim”.  
Existe para introduzir **evolução disciplinada**, com memória, prova, governação e rollback.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- arquitetura lógica do módulo LEARN;
- pipeline técnico de aprendizagem;
- recolha e preparação de histórico;
- análise de desempenho;
- geração de propostas;
- snapshots e versionamento;
- shadow mode / canary controlado;
- promoção de versões;
- rollback técnico;
- integração com CORE, DECISION, RISK, DASH e persistência;
- regras de segurança operacional da ativação;
- logging técnico e testes mínimos.

### 2.2 Excluído
Este documento não inclui:
- modelo matemático final de otimização;
- treino de modelos pesados/LLMs externos;
- ajuste livre de lógica crítica estrutural;
- UI detalhada do dashboard de aprendizagem;
- deployment distribuído de variantes em múltiplos nós.

---

## 3. Objetivos técnicos

O módulo LEARN deverá garantir, no mínimo:

1. **Evolução baseada em evidência**  
   Alterações só podem nascer de histórico analisável e suficientemente qualificado.

2. **Separação entre proposta, teste e ativação**  
   O sistema não deve saltar de análise para produção sem checkpoints de governação.

3. **Snapshots obrigatórios antes da mudança**  
   Nenhuma alteração relevante deve ser ativada sem snapshot anterior válido.

4. **Shadow mode antes de promoção plena**  
   Sempre que a política o exigir, versões candidatas devem ser observadas sem controlar produção real.

5. **Rollback rápido e auditável**  
   A reversão deve ser tecnicamente simples, rastreável e preservar histórico.

6. **Compatibilidade com risco e modo operacional**  
   O LEARN não pode ativar mudanças em contexto incompatível, instável ou inseguro.

7. **Uso controlado de memória histórica auxiliar**  
   O LEARN pode usar memória auxiliar para recuperar padrões e incidentes passados, desde que a evidência usada seja congelada e auditável.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-800 — LEARN
- FSD consolidado v0.5
- SDS-100 — CORE
- SDS-300 — DECISION
- SDS-400 — RISK
- SDS-600 — DASH
- ODIN-TRACEABILITY-MATRIX

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| O sistema deve analisar histórico operacional relevante | FSD-800 | `LearningHistoryCollector` + `PerformanceAnalyzer` |
| O sistema deve gerar propostas de alteração com racional | FSD-800 | `ChangeProposalBuilder` |
| O sistema deve criar snapshot antes de alterar versões ativas | FSD-800 | `VersionSnapshotStore` + `PreActivationSnapshotGuard` |
| O sistema deve suportar shadow mode/canary | FSD-800 / v0.3 | `ShadowEvaluationRunner` |
| O sistema deve conseguir rollback auditável | FSD-800 | `RollbackCoordinator` |
| O sistema deve respeitar governação de aprovação | FSD-800 | `ApprovalGate` + `ActivationGuard` |

---

## 5. Arquitetura lógica do LEARN

O LEARN deverá ser decomposto, no mínimo, nos seguintes componentes técnicos.

### 5.1 Componentes principais

| Componente | Responsabilidade técnica |
|---|---|
| `LearningOrchestrator` | coordena o pipeline completo do LEARN |
| `LearningHistoryCollector` | recolhe histórico relevante dos módulos |
| `LearningDatasetBuilder` | prepara dataset/snapshots de análise |
| `AuxiliaryMemoryMiner` | recupera memória histórica auxiliar relevante para análise |
| `PerformanceAnalyzer` | analisa desempenho por tática, contexto e versão |
| `ChangeProposalBuilder` | gera propostas de alteração formais |
| `ChangeBoundaryGuard` | valida fronteiras de alteração permitida |
| `VersionSnapshotStore` | guarda snapshots/versionamento |
| `ApprovalGate` | gere aprovação manual/automática limitada |
| `ShadowEvaluationRunner` | executa shadow mode/canary controlado |
| `PromotionEvaluator` | decide promoção de versão candidata |
| `ActivationGuard` | valida condições de ativação |
| `VersionPublisher` | publica versão ativa oficialmente |
| `RollbackCoordinator` | executa reversão para snapshot seguro |
| `LearnStatePublisher` | publica estado resumido do LEARN |
| `LearnAuditLogger` | logging estruturado do módulo |

---

## 6. Pipeline técnico de aprendizagem

### 6.1 Fases mínimas

Todo ciclo do LEARN deverá seguir, no mínimo, as seguintes fases:

1. recolha de histórico
2. preparação do dataset de análise
3. análise de desempenho
4. identificação de oportunidade de ajuste
5. geração de proposta formal
6. validação de fronteiras de alteração
7. criação de snapshot pré-ativação
8. aprovação (manual ou automática limitada)
9. shadow mode / teste controlado, quando exigido
10. avaliação de promoção
11. ativação da nova versão
12. monitorização pós-ativação
13. rollback, se necessário

### 6.2 Regra obrigatória
Nenhuma alteração deve saltar diretamente da fase 4 para produção sem passar por proposta, validação e snapshot.

---

## 7. Recolha e preparação de histórico

### 7.1 Objetivo
Construir uma base mínima de dados utilizáveis para aprendizagem e comparação.

### 7.2 Estrutura mínima: `learning_history_snapshot`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `history_snapshot_id` | Sim | ID do snapshot histórico |
| `created_at_utc` | Sim | timestamp |
| `time_window` | Sim | janela temporal analisada |
| `decision_records_ref` | Recomendado | referência aos ciclos decisórios |
| `execution_records_ref` | Recomendado | referência a execuções/resultados |
| `risk_records_ref` | Recomendado | referência a estados/bloqueios de risco |
| `market_context_ref` | Recomendado | contexto de mercado associado |
| `config_version_ref` | Sim | versão da configuração usada |
| `is_data_quality_sufficient` | Sim | qualidade mínima do histórico |
| `memory_advisory_refs` | Não | referências a memória auxiliar usada |

### 7.3 Regras obrigatórias
- histórico com qualidade insuficiente não deve alimentar promoção automática;
- incidentes graves, divergências e períodos anómalos devem ser identificáveis;
- o dataset deve ser versionado e referenciável.
- memória auxiliar pode enriquecer o histórico, mas não substituir registos oficiais de decisão, risco, execução ou recovery.

---

## 8. Análise de desempenho

### 8.1 Objetivo
Avaliar se o comportamento observado justifica alteração, manutenção ou suspensão.

### 8.2 Estrutura mínima: `performance_analysis_result`

| Campo | Obrigatório |
|---|---|
| `analysis_id` | Sim |
| `history_snapshot_id` | Sim |
| `evaluated_at_utc` | Sim |
| `tactic_performance_summary` | Sim |
| `context_performance_summary` | Recomendado |
| `frequency_vs_effectiveness_summary` | Recomendado |
| `stability_summary` | Sim |
| `degradation_flags` | Recomendado |
| `analysis_quality_class` | Sim |

### 8.3 Regras obrigatórias
- a análise deve distinguir degradação estrutural de ruído;
- métricas derivadas de histórico pobre devem ser marcadas como de baixa confiança;
- resultados usados para ativação automática devem cumprir critérios mais exigentes.

---

## 9. Fronteiras de alteração

### 9.1 Objetivo
Impedir que o LEARN altere parâmetros fora do envelope autorizado.

### 9.2 Estrutura mínima: `learning_change_policy`

| Campo | Obrigatório |
|---|---|
| `policy_id` | Sim |
| `allowed_change_types` | Sim |
| `protected_parameters` | Sim |
| `max_weight_delta` | Recomendado |
| `max_threshold_delta` | Recomendado |
| `min_evidence_quality_class` | Sim |
| `activation_mode_allowed` | Sim |
| `requires_shadow_mode` | Sim |

### 9.3 Regra obrigatória
Parâmetros protegidos não podem ser alterados automaticamente.

---

## 10. Proposta de alteração

### 10.1 Objetivo
Formalizar a alteração candidata antes de qualquer ativação.

### 10.2 Estrutura mínima: `change_proposal`

| Campo | Obrigatório |
|---|---|
| `proposal_id` | Sim |
| `created_at_utc` | Sim |
| `source_analysis_id` | Sim |
| `base_version_id` | Sim |
| `candidate_version_id` | Sim |
| `change_type` | Sim |
| `changed_parameters` | Sim |
| `old_values_ref` | Sim |
| `new_values_ref` | Sim |
| `reason_summary` | Sim |
| `evidence_summary` | Sim |
| `activation_mode` | Sim |
| `shadow_mode_required` | Sim |
| `rollback_trigger_hints` | Recomendado |
| `memory_evidence_refs` | Recomendado |

### 10.3 Regras obrigatórias
- não deve existir ativação sem proposta formal;
- proposta sem `base_version_id` ou sem referência a valores anteriores é inválida;
- proposta deve ser auditável e reproduzível.

---

## 11. Snapshot e versionamento

### 11.1 Objetivo
Garantir ponto de retorno seguro antes de qualquer mudança.

### 11.2 Estrutura mínima: `version_snapshot`

| Campo | Obrigatório |
|---|---|
| `snapshot_id` | Sim |
| `created_at_utc` | Sim |
| `version_id` | Sim |
| `snapshot_type` | Sim |
| `config_ref` | Sim |
| `weights_ref` | Recomendado |
| `thresholds_ref` | Recomendado |
| `metadata` | Recomendado |
| `is_recoverable` | Sim |

### 11.3 Tipos mínimos de snapshot
- `PRE_ACTIVATION`
- `ACTIVE_BASELINE`
- `ROLLBACK_TARGET`
- `SHADOW_BASELINE`

### 11.4 Regra obrigatória
Sem snapshot `PRE_ACTIVATION` válido, a ativação não pode avançar.

---

## 12. Governação de aprovação

### 12.1 Objetivo
Controlar quem ou o quê pode promover uma alteração.

### 12.2 Modos de aprovação

| Código | Nome | Descrição |
|---|---|---|
| AP-10 | MANUAL | requer validação humana explícita |
| AP-20 | AUTO_LIMITED | ativação automática limitada sob política estrita |
| AP-30 | SHADOW_THEN_APPROVE | testa primeiro em shadow, depois decide |

### 12.3 Estrutura mínima: `approval_state`

| Campo | Obrigatório |
|---|---|
| `proposal_id` | Sim |
| `approval_mode` | Sim |
| `approval_status` | Sim |
| `approved_by` | Não |
| `approved_at_utc` | Não |
| `approval_reason` | Recomendado |

### 12.4 Regra obrigatória
Em modo Real, alterações relevantes devem tender a exigir `MANUAL` ou `SHADOW_THEN_APPROVE`.

O estado resumido de approval pode coexistir com trilha histórica separada para auditoria.  
Approval atual não deve depender apenas de uma visão sobrescrita quando a auditoria exigir histórico por `proposal_id` ou por janela temporal.

---

## 13. Shadow mode / canary controlado

### 13.1 Objetivo
Comparar uma versão candidata com a versão ativa sem lhe dar controlo pleno da produção real.

### 13.2 Estrutura mínima: `shadow_evaluation_session`

| Campo | Obrigatório |
|---|---|
| `shadow_session_id` | Sim |
| `proposal_id` | Sim |
| `candidate_version_id` | Sim |
| `baseline_version_id` | Sim |
| `started_at_utc` | Sim |
| `ended_at_utc` | Não |
| `evaluation_scope` | Sim |
| `comparison_summary` | Não |
| `promotion_recommendation` | Não |

### 13.3 Modos possíveis de shadow
- reprocessamento de histórico recente;
- avaliação em tempo real sem emissão de ordens reais;
- comparação lado a lado de score/decisão com a versão ativa.

### 13.4 Regras obrigatórias
- a versão candidata em shadow não pode comandar execução real;
- os resultados devem ser comparáveis à baseline;
- o shadow mode deve ter tempo/janela mínima de observação quando exigido pela política.

---

## 14. Promoção de versão

### 14.1 Objetivo
Transformar uma versão candidata em versão ativa oficial.

### 14.2 Estrutura mínima: `promotion_decision`

| Campo | Obrigatório |
|---|---|
| `promotion_id` | Sim |
| `proposal_id` | Sim |
| `candidate_version_id` | Sim |
| `baseline_version_id` | Sim |
| `evaluated_at_utc` | Sim |
| `promotion_result` | Sim |
| `reason_summary` | Sim |
| `requires_restricted_activation` | Recomendado |

### 14.3 Resultados mínimos
- `PROMOTE`
- `PROMOTE_RESTRICTED`
- `HOLD`
- `REJECT`
- `ROLLBACK_REQUIRED`

### 14.4 Regra obrigatória
Promoção não deve acontecer se:
- a política exigir shadow e o shadow não estiver concluído;
- não existir snapshot válido;
- o risco/CORE publicarem estado incompatível com ativação.
- approval estiver `PENDING`, `REJECTED` ou `BLOCKED`;
- o shadow recomendar `REJECT` ou `ROLLBACK_REQUIRED`.

Quando a ativação for bloqueada, o motivo deve ser auditável e propagável ao DASH através de `blocking_reason_code` e `blocking_summary`.

---

## 15. Ativação de nova versão

### 15.1 Objetivo
Publicar uma nova versão ativa de forma controlada e rastreável.

### 15.2 Estrutura mínima: `version_activation_record`

| Campo | Obrigatório |
|---|---|
| `activation_id` | Sim |
| `version_id` | Sim |
| `previous_version_id` | Sim |
| `activated_at_utc` | Sim |
| `activation_mode` | Sim |
| `activated_by` | Não |
| `restricted_post_activation` | Sim |
| `post_activation_monitoring_policy` | Recomendado |

### 15.3 Regras obrigatórias
- só pode existir uma versão ativa por domínio decisório relevante, salvo política explícita de teste paralelo;
- toda ativação deve ser publicada ao CORE, DECISION e DASH;
- ativação deve ser reversível.

---

## 16. Monitorização pós-ativação

### 16.1 Objetivo
Verificar se a nova versão se comporta dentro do esperado.

### 16.2 Estrutura mínima: `post_activation_monitoring_result`

| Campo | Obrigatório |
|---|---|
| `activation_id` | Sim |
| `version_id` | Sim |
| `monitoring_window` | Sim |
| `baseline_comparison_summary` | Recomendado |
| `degradation_detected` | Sim |
| `rollback_recommended` | Sim |
| `observed_risk_flags` | Recomendado |

### 16.3 Regra obrigatória
Uma nova versão não deve ser considerada estável só porque ativou sem erro técnico.

---

## 17. Rollback técnico

### 17.1 Objetivo
Regressar a um snapshot seguro quando a nova versão falha ou degrada.

### 17.2 Estrutura mínima: `rollback_record`

| Campo | Obrigatório |
|---|---|
| `rollback_id` | Sim |
| `triggered_at_utc` | Sim |
| `from_version_id` | Sim |
| `to_snapshot_id` | Sim |
| `to_version_id` | Sim |
| `rollback_reason` | Sim |
| `triggered_by` | Não |
| `rollback_result` | Sim |

### 17.3 Regras obrigatórias
- rollback não pode apagar histórico da versão revertida;
- rollback deve ser auditável;
- após rollback, a baseline anterior volta a ser a referência ativa;
- dependendo da política, pode ser exigida observação reforçada após rollback.
- rollback deve ser bloqueado se não existir versão ativa;
- rollback deve ser bloqueado se não existir snapshot recuperável.

---

## 18. Estados internos do LEARN

### 18.1 Estados canónicos recomendados

| Código | Nome |
|---|---|
| LS-10 | INACTIVE |
| LS-20 | COLLECTING_HISTORY |
| LS-30 | ANALYZING |
| LS-40 | PROPOSAL_GENERATED |
| LS-50 | WAITING_APPROVAL |
| LS-60 | PREPARING_ACTIVATION |
| LS-70 | SHADOW_RUNNING |
| LS-80 | VERSION_ACTIVE_MONITORING |
| LS-90 | ROLLED_BACK |
| LS-100 | LEARN_BLOCKED |
| LS-110 | LEARN_ERROR |

### 18.2 Regra obrigatória
O estado interno deve ser publicado ao DASH e ser coerente com a fase do pipeline.

---

## 19. Interfaces técnicas

### 19.1 Interface com CORE
O LEARN deve consumir do CORE:
- `current_mode`
- `global_state`
- `active_block_vector_summary`
- `critical_flags`
- indicação de que a ativação é ou não permitida

O LEARN deve publicar ao CORE:
- `EV-LEARN-VERSION-ACTIVATED`
- `EV-LEARN-ROLLBACK`
- `EV-LEARN-BLOCKED`
- eventos de falha relevante, quando afetem a operação

### 19.2 Interface com DECISION
O LEARN deve consumir do DECISION:
- métricas de score histórico;
- eficácia por tática;
- racional resumido por ciclo;
- versão da configuração usada.

O DECISION deve consumir do LEARN:
- nova versão ativa oficial;
- versão revertida, quando aplicável.

### 19.3 Interface com RISK
O LEARN deve consumir do RISK:
- estado atual de risco;
- restrições de ativação;
- sinal de contexto incompatível com promoção;
- envelope conservador recomendado para pós-ativação.

### 19.4 Interface com DASH
O LEARN deve publicar ao DASH:
- `learn_state`
- `active_version`
- `pending_proposal`
- `last_change_summary`
- `approval_status`
- `rollback_state`
- `learn_shadow_audit`
- `learn_operational_hints`
- `learn_query_results`

No corte atual, a interface operacional com o DASH também inclui ações explícitas de dispatch:
- `LEARN_ACTION_REVIEW_APPROVAL`
- `LEARN_ACTION_EVALUATE_PROMOTION`
- `LEARN_ACTION_START_SHADOW`
- `LEARN_ACTION_COMPLETE_SHADOW`
- `LEARN_ACTION_ACTIVATE_PROPOSAL`
- `LEARN_ACTION_TRIGGER_ROLLBACK`

Queries explícitas mínimas publicadas via `learn_query_results`:
- `LEARN_QUERY_PROPOSAL`
- `LEARN_QUERY_APPROVAL`
- `LEARN_QUERY_SHADOW_AUDIT`
- `LEARN_QUERY_SHADOW_RECOMMENDATION`
- `LEARN_QUERY_ACTIVE_VERSION`
- `LEARN_QUERY_ROLLBACK_AUDIT`

Quando uma ação LEARN for rejeitada, o resultado público deve poder expor:
- `accepted`
- `blocking_reason_code`
- `blocking_summary`

### 19.5 Interface com persistência
O LEARN deverá armazenar, no mínimo:
- propostas;
- snapshots;
- versões ativas e antigas;
- estado atual de approval e trilha histórica de approval;
- shadow sessions;
- promoções;
- rollbacks.

Regras obrigatórias:
- a persistência deve suportar leituras `latest` e leituras auditáveis por `proposal_id` ou janela temporal;
- approvals, shadow sessions e promotion decisions devem poder ser listados por `proposal_id`;
- rollback records devem poder ser listados por versão e por janela temporal;
- a trilha auditável não deve depender apenas do último registo disponível.

### 19.6 Interface com memória auxiliar
O LEARN pode consumir de uma camada de memória auxiliar:
- racional histórico recuperado semanticamente;
- incidentes e pós-mortems relevantes;
- decisões semelhantes por contexto, tática ou regime de mercado;
- resultados de testes e shadow sessions antigas.

Regras obrigatórias:
- memória auxiliar nunca substitui os registos oficiais persistidos;
- qualquer evidência usada numa proposta deve ser referenciável e congelada;
- indisponibilidade desta interface não pode forçar promoção ou rollback.

---

## 20. Regras de compatibilidade com modos operacionais

### 20.1 Regras obrigatórias
- em `MD-30 REAL`, ativação automática deve ser mais restrita;
- em `MD-40 TRAINING`, o sistema pode permitir mais liberdade de avaliação e shadow;
- em `MD-50 MAINTENANCE`, ativação pode ser técnica, mas deve continuar auditável;
- em contexto de kill ativo ou bloqueio crítico, o LEARN não deve promover versão.

### 20.2 Fallback
Se o contexto operacional for incompatível:
- a proposta pode existir;
- a ativação deve ser adiada ou bloqueada.

---

## 21. Logging técnico do LEARN

### 21.1 Eventos mínimos a registar
- recolha de histórico iniciada;
- análise concluída;
- proposta gerada;
- violação de fronteira de alteração;
- snapshot criado;
- aprovação recebida/rejeitada;
- shadow mode iniciado/concluído;
- promoção aceite/rejeitada;
- ativação concluída;
- rollback executado;
- bloqueio do processo de aprendizagem;
- erro técnico de aprendizagem.

### 21.2 Campos mínimos
- `proposal_id`
- `version_id`
- `snapshot_id` quando aplicável
- `learn_state`
- `event_type`
- `reason_summary`
- `timestamp_utc`
- `severity`

### 21.3 Regra obrigatória
Os logs devem permitir reconstruir o caminho completo:
histórico -> proposta -> snapshot -> shadow -> promoção -> ativação/rollback.

---

## 22. Estrutura técnica recomendada de código

```text
odin/
├── src/
│   ├── learn/
│   │   ├── orchestrator/
│   │   ├── history/
│   │   ├── dataset/
│   │   ├── analysis/
│   │   ├── proposals/
│   │   ├── boundaries/
│   │   ├── snapshots/
│   │   ├── approval/
│   │   ├── shadow/
│   │   ├── promotion/
│   │   ├── activation/
│   │   ├── rollback/
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

## 23. Testes técnicos mínimos

### 23.1 Unit tests
- validação de fronteiras de alteração;
- geração de proposta;
- criação de snapshot;
- cálculo de promoção;
- regras de rollback;
- consistência de estados internos.

### 23.2 Integration tests
- geração de proposta com histórico suficiente;
- bloqueio de alteração a parâmetro protegido;
- ativação com snapshot válido;
- shadow mode sem emissão de ordens reais;
- promoção após shadow;
- rollback após degradação;
- tentativa de ativação com kill ativo.

### 23.3 Fault-injection tests
- snapshot inválido;
- proposta incompleta;
- falha a meio da ativação;
- shadow inconclusivo;
- rollback sem snapshot recuperável;
- incompatibilidade entre CORE/RISK e ativação.

---

## 24. Critérios de aceitação

O SDS-800 — LEARN será considerado tecnicamente suficiente quando:

1. o pipeline de aprendizagem puder ser implementado sem ambiguidades críticas;
2. histórico, proposta, snapshot, shadow, ativação e rollback estiverem tecnicamente separados;
3. nenhuma ativação relevante puder ocorrer sem snapshot válido;
4. o sistema suportar shadow mode sem tocar produção real;
5. a promoção depender de critérios explícitos;
6. o rollback puder devolver o sistema a versão segura;
7. a ativação respeitar CORE, RISK e o modo operacional;
8. o ciclo completo for auditável e testável.

---

## 25. Dependências e fecho do pacote principal

### 25.1 Dependências principais
- SDS-100 — CORE
- SDS-300 — DECISION
- SDS-400 — RISK
- SDS-600 — DASH
- ODIN-TRACEABILITY-MATRIX

### 25.2 Observação
Com este documento, o pacote principal de SDS do Odin fica funcionalmente muito próximo de estar fechado.

---

## 26. Conclusão

O SDS-800 fecha a camada técnica da evolução controlada do Odin.

Sem este documento, a aprendizagem correria o risco de ser:
- opaca;
- demasiado agressiva;
- sem rollback;
- sem snapshots;
- sem fronteiras.

Com este documento, o LEARN passa a ser uma camada disciplinada de evolução:
- baseada em evidência;
- com governação;
- testável;
- reversível;
- compatível com produção real.

Num sistema destes, aprender não pode significar mexer em tudo. Tem de significar melhorar sem perder controlo.
