# SDS-700 — RECOVERY
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Arquitetura técnica do módulo RECOVERY, deteção de incidentes, reconstrução de estado, reconciliação, retoma segura, bloqueio por incerteza e coordenação com CORE, EXEC, MARKET e RISK.

---

## 1. Finalidade do documento

Este documento define a especificação técnica do módulo **RECOVERY** do Odin.

Se o FSD-700 define **o que** o sistema deve fazer perante falhas e incidentes, este SDS-700 define **como** o módulo RECOVERY deve ser estruturado para:
- detetar incidentes relevantes;
- recolher contexto persistido e estado observado;
- reconciliar fontes de verdade potencialmente divergentes;
- determinar se a recuperação foi validada, restrita, inconclusiva ou falhada;
- coordenar com o CORE a retoma segura ou a manutenção de bloqueio;
- impedir retorno cego à operação normal.

O RECOVERY é a camada que transforma falha em processo controlado, em vez de deixar o sistema regressar com memória parcial e confiança fictícia.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- arquitetura lógica do módulo RECOVERY;
- pipeline técnico de recuperação;
- classificação técnica de incidentes;
- modelo de reconstrução de estado;
- reconciliação entre estado persistido e estado observado;
- critérios técnicos de confiança da recuperação;
- outputs do recovery para o CORE;
- integração com persistência, EXEC, MARKET, RISK e DASH;
- regras de timeout, bloqueio e intervenção humana;
- logging técnico e testes mínimos.

### 2.2 Excluído
Este documento não inclui:
- algoritmo detalhado do broker;
- desenho visual do dashboard de incidentes;
- política de alta disponibilidade distribuída;
- backup cloud;
- mecanismos avançados de replicação ou clustering.

---

## 3. Objetivos técnicos

O módulo RECOVERY deverá garantir, no mínimo:

1. **Reação controlada a incidentes**  
   O sistema deve saber entrar em fluxo de recovery de forma determinística.

2. **Reconstrução baseada em evidência**  
   A recuperação deve usar:
   - estado persistido;
   - estado observado externo;
   - resultados executórios;
   - bloqueios ativos;
   - contexto de mercado e risco.

3. **Incerteza tratada como risco**  
   Se o sistema não conseguir determinar o estado com confiança suficiente, deve permanecer bloqueado ou degradado.

4. **Retoma segura e nunca direta para operação ativa**  
   Recovery validado não deve levar diretamente a `ACTIVE`.

5. **Intervenção humana explícita quando necessária**  
   O sistema deve sinalizar quando não consegue fechar o incidente autonomamente.

6. **Auditabilidade integral**  
   O processo de recovery deve poder ser reconstruído tecnicamente.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-700 — RECOVERY
- FSD consolidado v0.5
- SDS-100 — CORE
- SDS-110 — CORE-PERSISTENCE
- SDS-120 — CORE-INTERFACES
- SDS-500 — EXEC
- SDS-200 — MARKET
- SDS-400 — RISK
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| O sistema deve reconstruir estado após incidente | FSD-700 | `RecoveryOrchestrator` + `StateReconstructor` |
| O sistema deve reconciliar estado persistido e observado | FSD-700 | `ReconciliationEngine` |
| O sistema deve distinguir recovery validado, restrito, inconclusivo e falhado | FSD-700 | `RecoveryClassifier` |
| Recovery não pode limpar kill persistente nem bloqueio manual | FSD-700 / v0.4+ | `BlockPrecedenceGuard` |
| Recovery nunca regressa diretamente a ACTIVE | FSD-700 / CORE model | `RecoveryExitGuard` |

---

## 5. Arquitetura lógica do RECOVERY

O RECOVERY deverá ser decomposto, no mínimo, nos seguintes componentes técnicos.

### 5.1 Componentes principais

| Componente | Responsabilidade técnica |
|---|---|
| `RecoveryOrchestrator` | coordena o ciclo completo de recovery |
| `IncidentClassifier` | classifica o tipo e severidade do incidente |
| `RecoveryContextLoader` | recolhe snapshots persistidos e contexto local |
| `ObservedStateCollector` | recolhe estado observado dos módulos críticos |
| `StateReconstructor` | reconstrói o estado técnico mais provável |
| `ReconciliationEngine` | compara persistido vs observado |
| `RecoveryConfidenceEvaluator` | calcula confiança mínima da recuperação |
| `RecoveryClassifier` | determina resultado final do recovery |
| `RecoveryExitGuard` | controla saída de recovery para estados permitidos |
| `InterventionResolver` | determina necessidade de ação humana |
| `RecoveryStatePublisher` | publica estado e resultado do recovery |
| `RecoveryAuditLogger` | logging estruturado do recovery |

---

## 6. Classificação técnica de incidentes

### 6.1 Tipos canónicos de incidente

| Código | Tipo | Descrição resumida |
|---|---|---|
| INC-10 | UNEXPECTED_RESTART | reinício não limpo |
| INC-20 | POWER_LOSS | falha de energia |
| INC-30 | COMMUNICATION_LOSS | perda de internet/comunicação crítica |
| INC-40 | FEED_LOSS | perda prolongada de feed |
| INC-50 | EXEC_DIVERGENCE | divergência executória |
| INC-60 | PERSISTENCE_INCONSISTENT | estado persistido inconsistente |
| INC-70 | CRITICAL_MODULE_TIMEOUT | timeout de módulo crítico |
| INC-80 | MANUAL_RECOVERY_REQUEST | pedido manual de validação/recovery |

### 6.2 Classificação de recuperabilidade

| Classe | Significado |
|---|---|
| `RECOVERABLE` | recuperável sem intervenção humana obrigatória, se a confiança for suficiente |
| `RECOVERABLE_RESTRICTED` | recuperável, mas só com regresso degradado |
| `UNCERTAIN` | não há confiança suficiente para retoma normal |
| `FATAL_OR_MANUAL` | exige intervenção humana explícita |

### 6.3 Regra obrigatória
A classificação do incidente deve ser armazenada e publicada como parte do estado de recovery.

---

## 7. Pipeline técnico de recovery

### 7.1 Fases mínimas

Todo ciclo de recovery deverá seguir, no mínimo, as seguintes fases:

1. deteção/receção do incidente
2. classificação do incidente
3. carregamento do contexto persistido
4. recolha do estado observado atual
5. reconstrução de estado provável
6. reconciliação persistido vs observado
7. avaliação de confiança
8. classificação do resultado do recovery
9. publicação do resultado
10. autorização ou negação de saída de recovery

### 7.2 Regra obrigatória
Nenhuma fase pode assumir sucesso silencioso se a anterior tiver falhado ou devolvido estado inconclusivo.

---

## 8. Contexto técnico de recovery

### 8.1 Estrutura mínima: `recovery_context`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `recovery_id` | Sim | ID único do ciclo de recovery |
| `incident_type` | Sim | tipo de incidente |
| `trigger_event_id` | Sim | evento detonador |
| `started_at_utc` | Sim | início do recovery |
| `persisted_core_snapshot_ref` | Não | referência ao snapshot persistido |
| `persisted_block_vector_ref` | Não | referência ao vetor de bloqueios |
| `persisted_kill_flag_ref` | Não | referência ao kill persistido |
| `persisted_recovery_snapshot_ref` | Não | snapshot anterior de recovery |
| `current_observed_state_ref` | Não | referência ao estado observado |
| `recovery_mode` | Sim | automático, restrito, manual-assistido |

### 8.2 Regra obrigatória
Todo ciclo de recovery deve ser identificável univocamente por `recovery_id`.

---

## 9. Estado observado

### 9.1 Objetivo
Permitir ao recovery avaliar o que o sistema e o ambiente externo “mostram agora”, em vez de depender só da persistência.

### 9.2 Estrutura mínima: `observed_state_snapshot`

| Campo | Obrigatório |
|---|---|
| `observed_snapshot_id` | Sim |
| `collected_at_utc` | Sim |
| `core_runtime_marker_state` | Recomendado |
| `market_state` | Não |
| `risk_state` | Não |
| `kill_active_observed` | Recomendado |
| `exec_state_summary` | Não |
| `last_known_intent_state` | Não |
| `heartbeat_health_summary` | Recomendado |
| `module_availability_map` | Sim |

### 9.3 Regra obrigatória
O observed state deve incluir explicitamente ausência de dados, e não omitir campos como se tudo estivesse normal.

---

## 10. Reconstrução de estado

### 10.1 Objetivo
Produzir uma hipótese técnica do estado atual real do sistema.

### 10.2 Estrutura mínima: `reconstructed_state`

| Campo | Obrigatório |
|---|---|
| `recovery_id` | Sim |
| `reconstructed_global_state` | Sim |
| `reconstructed_mode` | Recomendado |
| `reconstructed_block_vector` | Sim |
| `reconstructed_exec_status` | Recomendado |
| `reconstructed_market_status` | Recomendado |
| `reconstructed_risk_status` | Recomendado |
| `confidence_inputs_summary` | Sim |

### 10.3 Regras obrigatórias
- o reconstructed state não deve ser tratado como facto absoluto;
- deve ser acompanhado de confiança e origem das evidências;
- ausência de evidência suficiente deve degradar a confiança.

---

## 11. Reconciliação técnica

### 11.1 Objetivo
Comparar o que estava persistido com o que foi observado/reconstruído.

### 11.2 Estrutura mínima: `reconciliation_result`

| Campo | Obrigatório |
|---|---|
| `recovery_id` | Sim |
| `is_consistent` | Sim |
| `consistency_grade` | Sim |
| `conflicts_detected` | Sim |
| `block_vector_consistency` | Recomendado |
| `kill_consistency` | Recomendado |
| `exec_consistency` | Recomendado |
| `market_consistency` | Recomendado |
| `notes` | Não |

### 11.3 Graus de consistência recomendados
- `CONSISTENT`
- `CONSISTENT_WITH_RESTRICTIONS`
- `INCONCLUSIVE`
- `DIVERGENT`

### 11.4 Regra obrigatória
`DIVERGENT` ou `INCONCLUSIVE` não podem permitir saída normal do recovery.

---

## 12. Avaliação de confiança

### 12.1 Objetivo
Transformar a reconciliação em decisão técnica de recuperação.

### 12.2 Estrutura mínima: `recovery_confidence_result`

| Campo | Obrigatório |
|---|---|
| `recovery_id` | Sim |
| `confidence_score` | Sim |
| `confidence_class` | Sim |
| `missing_critical_evidence` | Sim |
| `manual_intervention_recommended` | Sim |
| `safe_to_exit_recovery` | Sim |

### 12.3 Classes recomendadas
- `HIGH`
- `MEDIUM_RESTRICTED`
- `LOW`
- `UNSAFE`

### 12.4 Regra obrigatória
`LOW` ou `UNSAFE` devem impedir retoma normal.

---

## 13. Resultado técnico do recovery

### 13.1 Estrutura mínima: `recovery_result`

| Campo | Obrigatório |
|---|---|
| `recovery_id` | Sim |
| `result_code` | Sim |
| `result_summary` | Sim |
| `target_post_recovery_state` | Não |
| `manual_intervention_required` | Sim |
| `block_vector_after_recovery` | Sim |
| `published_at_utc` | Sim |

### 13.2 Valores mínimos de `result_code`
- `RCV-10 VALIDATED`
- `RCV-20 VALIDATED_RESTRICTED`
- `RCV-30 INCONCLUSIVE`
- `RCV-40 FAILED`
- `RCV-50 MANUAL_REQUIRED`

### 13.3 Regra obrigatória
O recovery deve produzir um resultado único e publicável por ciclo.

---

## 14. Saída de recovery e guards

### 14.1 Objetivo
Controlar a transição de `ST-100 RECOVERY` para outro estado.

### 14.2 Guards mínimos do `RecoveryExitGuard`
Para sair de recovery, devem ser verdadeiros, no mínimo:
- `recovery_result` compatível;
- `kill_persistent_not_active` ou kill tratado explicitamente;
- `manual_block_not_pending`, se aplicável;
- `reconciliation_not_inconclusive`;
- `target_state_allowed_by_core`.

### 14.3 Regra obrigatória
As únicas saídas normais de recovery devem apontar para:
- `ST-20 IDLE`
- `ST-30 MONITORING`

### 14.4 Proibição
Recovery não pode sair diretamente para:
- `ST-50 ACTIVE`

---

## 15. Regras de precedência e bloqueio

### 15.1 Regras obrigatórias
- recovery validado não limpa bloqueio manual;
- recovery validado não limpa kill persistente;
- `EV-RECOVERY-OK` não tem precedência sobre `EV-KILL-ACTIVE`;
- se coexistirem bloqueios, o `BlockPrecedenceGuard` do CORE continua soberano.

### 15.2 Implicação técnica
O RECOVERY pode propor um estado seguro, mas não decide sozinho desbloqueios de maior precedência.

---

## 16. Integração técnica com persistência

### 16.1 Dependência do `PersistentStateStore`
O RECOVERY deverá ler, no mínimo:
- `core_runtime_marker`
- `core_state_snapshot`
- `core_kill_flag`
- `core_block_vector_snapshot`
- `core_recovery_snapshot`

### 16.2 Escritas mínimas do RECOVERY
O RECOVERY deverá escrever, no mínimo:
- novo `core_recovery_snapshot` do incidente atual;
- referência ao resultado final do recovery;
- observações de intervenção humana obrigatória, quando aplicável.

### 16.3 Regra obrigatória
Falha de leitura de persistência crítica deve degradar fortemente a confiança do recovery.

---

## 17. Integração técnica com EXEC

### 17.1 Inputs mínimos do EXEC para o RECOVERY
- estado executório resumido;
- última intenção conhecida;
- divergência ativa ou histórica recente;
- resultado consolidado mais recente;
- pendência executória relevante.

### 17.2 Regras obrigatórias
- divergência executória deve ter peso alto na classificação do incidente;
- estado executório desconhecido em contexto crítico deve reduzir confiança;
- EXEC pendente sem confirmação suficiente pode impedir saída de recovery.

---

## 18. Integração técnica com MARKET

### 18.1 Inputs mínimos do MARKET para o RECOVERY
- estado de mercado atual;
- integridade do feed;
- última atualização válida;
- contexto atual resumido.

### 18.2 Regras obrigatórias
- MARKET indisponível não deve impedir todo o recovery em absoluto, mas deve impedir retoma operacional plena;
- ausência de confirmação do MARKET deve favorecer saída para `MONITORING` ou bloqueio, não para atividade.

---

## 19. Integração técnica com RISK

### 19.1 Inputs mínimos do RISK para o RECOVERY
- `risk_state`
- `kill_active`
- `restriction_flags`
- `dominant_risk_reason`

### 19.2 Regras obrigatórias
- kill ativo ou persistente deve dominar o resultado do recovery;
- recovery validado com risco restritivo deve convergir para estado restrito/degradado, não para atividade.

---

## 20. Integração técnica com CORE

### 20.1 Inputs mínimos do CORE para o RECOVERY
- estado global atual;
- modo atual;
- vetor de bloqueios atual;
- motivo dominante;
- tipo de trigger do recovery.

### 20.2 Outputs mínimos do RECOVERY para o CORE
- `EV-RECOVERY-START`
- `EV-RECOVERY-OK`
- `EV-RECOVERY-OK-RESTRICTED`
- `EV-RECOVERY-FAIL`
- `EV-RECOVERY-INTERVENTION-REQUIRED`

### 20.3 Regra obrigatória
O CORE continua a ser a autoridade sobre a transição global de estado.

---

## 21. Integração técnica com DASH

### 21.1 Outputs mínimos do RECOVERY para o DASH
- `recovery_state`
- `incident_type`
- `recovery_result`
- `manual_intervention_required`
- `reconciliation_confidence`
- `result_summary`

### 21.2 Regra obrigatória
O DASH deve poder distinguir claramente:
- recovery em curso;
- recovery validado;
- recovery validado com restrições;
- recovery inconclusivo;
- recovery falhado.

---

## 22. Timeouts e fallback

### 22.1 Timeouts mínimos a modelar
- timeout de recolha de estado observado;
- timeout de resposta de EXEC relevante para recovery;
- timeout de leitura de persistência crítica;
- timeout global do ciclo de recovery.

### 22.2 Fallback recomendado
Se o ciclo de recovery exceder o timeout sem confiança suficiente:
- classificar como `INCONCLUSIVE` ou `MANUAL_REQUIRED`;
- manter estado seguro/bloqueado;
- registar evento crítico.

### 22.3 Regra obrigatória
Recovery lento e inconclusivo não pode ser tratado como recovery bem-sucedido.

---

## 23. Logging técnico do RECOVERY

### 23.1 Eventos mínimos a registar
- incidente recebido;
- classificação do incidente;
- contexto persistido carregado;
- estado observado recolhido;
- reconstrução concluída;
- reconciliação concluída;
- avaliação de confiança;
- resultado final do recovery;
- necessidade de intervenção humana;
- saída de recovery aprovada ou negada.

### 23.2 Campos mínimos
- `recovery_id`
- `incident_type`
- `recovery_phase`
- `confidence_class`
- `result_code`
- `timestamp_utc`
- `severity`
- `reason_summary`

### 23.3 Regra obrigatória
Os logs devem permitir reconstruir o ciclo completo de recovery.

---

## 24. Estrutura técnica recomendada de código

```text
odin/
├── src/
│   ├── recovery/
│   │   ├── orchestrator/
│   │   ├── incident_classifier/
│   │   ├── context_loader/
│   │   ├── observed_state/
│   │   ├── reconstruction/
│   │   ├── reconciliation/
│   │   ├── confidence/
│   │   ├── exit_guard/
│   │   ├── intervention/
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
- classificação de incidente;
- reconstrução de estado;
- reconciliação consistente/inconclusiva/divergente;
- avaliação de confiança;
- guards de saída de recovery.

### 25.2 Integration tests
- reinício inesperado com estado persistido válido;
- reinício com kill persistente ativo;
- divergência executória seguida de recovery;
- perda prolongada de feed;
- recovery validado com saída para `MONITORING`;
- recovery inconclusivo com bloqueio mantido;
- recovery validado sem limpar bloqueio manual.

### 25.3 Fault-injection tests
- persistência corrompida;
- EXEC sem estado observável;
- MARKET indisponível durante recovery;
- timeout do próprio ciclo de recovery;
- estado observado parcial e contraditório.

---

## 26. Critérios de aceitação

O SDS-700 — RECOVERY será considerado tecnicamente suficiente quando:

1. o módulo conseguir processar incidentes por pipeline claro;
2. estado persistido e observado puderem ser reconciliados;
3. a confiança da recuperação puder ser classificada tecnicamente;
4. recovery validado, restrito, inconclusivo e falhado estiverem bem distinguidos;
5. kill persistente e bloqueio manual não puderem ser limpos indevidamente;
6. a saída de recovery nunca permitir salto direto para `ACTIVE`;
7. o sistema puder manter bloqueio por incerteza de forma justificável;
8. o ciclo completo puder ser auditado e testado.

---

## 27. Dependências e próximos documentos

### 27.1 Dependências principais
- SDS-100 — CORE
- SDS-110 — CORE-PERSISTENCE
- SDS-120 — CORE-INTERFACES
- SDS-200 — MARKET
- SDS-400 — RISK
- SDS-500 — EXEC
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 27.2 Próximo documento recomendado
1. **SDS-800 — LEARN**

---

## 28. Conclusão

O SDS-700 fecha a camada técnica da resiliência do Odin.

Sem este documento, o sistema poderia:
- arrancar após falha com falsa confiança;
- perder noção do que estava ativo;
- limpar bloqueios indevidamente;
- confundir “consegui arrancar” com “recuperei com segurança”.

Com este documento, o recovery passa a ser:
- estruturado;
- mensurável;
- conservador;
- auditável;
- integrado com o CORE e com o estado real observado.

Num sistema destes, falhar não é o maior problema. O maior problema é voltar a operar sem saber se realmente recuperou.
