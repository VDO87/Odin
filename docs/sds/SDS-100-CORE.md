# SDS-100 — CORE
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Núcleo técnico do sistema, autoridade de estado global, serialização de eventos, guards, bloqueios, modos operacionais, heartbeat e publicação do estado oficial.

---

## 1. Finalidade do documento

Este documento define a especificação técnica do módulo **CORE** do Odin.

Se o FSD-100 fixa a missão funcional do núcleo e o `ODIN-CORE-STATE-AND-EVENT-MODEL` estabiliza estados, modos, eventos e precedências, o SDS-100 define **como o núcleo deve ser implementado tecnicamente** para que o resto do sistema opere sobre uma autoridade de estado única, auditável e fail-safe.

Sem este documento, o risco é elevado:
- persistência a assumir regras que o CORE nunca formalizou;
- interfaces a depender de semânticas implícitas;
- bloqueios e transições a divergir entre módulos;
- concorrência a introduzir incoerência de estado demasiado cedo.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- arquitetura lógica do CORE;
- responsabilidades técnicas do runtime central;
- state machine do sistema;
- serialização de eventos críticos;
- guards de transição;
- gestão do vetor de bloqueios ativos;
- supervisão de heartbeat/liveness;
- gestão do modo operacional ativo;
- publicação do estado global oficial;
- integração obrigatória com persistência e interfaces;
- regras de arranque, paragem e fail-safe;
- contratos técnicos centrais do núcleo;
- testes mínimos do CORE.

### 2.2 Excluído
Este documento não inclui:
- backend concreto de persistência final;
- binding físico definitivo das interfaces;
- UI do DASH;
- scoring do DECISION;
- lógica específica de broker/exchange;
- evolução automática do LEARN.

---

## 3. Objetivos técnicos

O CORE deverá garantir, no mínimo:

1. **Autoridade única de estado**  
   O sistema deve ter uma única fonte oficial para estado global, modo ativo e bloqueios consolidados.

2. **Transições seguras e auditáveis**  
   Toda transição relevante deve ser validada por guards explícitos e ficar reconstruível por logs e snapshots.

3. **Serialização determinística de eventos**  
   O núcleo não deve permitir mutações concorrentes de estado no MVP.

4. **Fail-safe por defeito**  
   Falha de módulo crítico, persistência inconsistente, kill ativo ou heartbeat expirado devem convergir para estado seguro.

5. **Precedência transversal coerente**  
   Kill, falha, recovery e risco devem obedecer à mesma hierarquia em todo o sistema.

6. **Publicação estável do estado global**  
   Os restantes módulos e o operador devem observar um read-model oficial, estável e semanticamente consistente.

7. **Preparação real para recovery**  
   O CORE deve deixar evidência suficiente para restart seguro e entrada disciplinada em recovery.

8. **Separação dura entre autoridade e memória auxiliar**  
   O CORE nunca deve tratar memória semântica auxiliar como fonte oficial de estado, bloqueio, kill ou recuperação.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-000 — MASTER
- FSD-100 — CORE
- FSD-400 — RISK
- FSD-700 — RECOVERY
- FSD consolidado v0.5
- `ODIN-CORE-STATE-AND-EVENT-MODEL`
- `ODIN-TRACEABILITY-MATRIX`
- SDS-110 — CORE-PERSISTENCE
- SDS-120 — CORE-INTERFACES

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| manter estado global único e coerente | FSD-100 / REQ-CORE-001 | `CoreStateMachine` + `GlobalStatePublisher` |
| rejeitar transições inválidas | FSD-100 / REQ-CORE-002 | `TransitionGuardEngine` + matriz de transições |
| supervisionar heartbeat de módulos críticos | FSD-100 / REQ-CORE-003 | `HeartbeatSupervisor` |
| validar kill persistente no arranque | FSD-100 / REQ-CORE-004 | `StartupOrchestrator` + integração com `PersistentStateStore` |
| manter vetor completo de bloqueios ativos | FSD-100 / REQ-CORE-005 | `BlockManager` + `active_block_vector` |
| impedir recovery -> operação ativa direta | FSD-100 / REQ-CORE-006 | regras duras da state machine |

---

## 5. Arquitetura lógica do CORE

O módulo CORE deverá ser decomposto, no mínimo, nos seguintes componentes técnicos:

- `StartupOrchestrator`
- `CoreRuntimeController`
- `CoreEventInbox`
- `CoreStateMachine`
- `TransitionGuardEngine`
- `BlockManager`
- `ModePolicyEvaluator`
- `HeartbeatSupervisor`
- `GlobalStatePublisher`
- `CriticalTransitionRecorder`

### 5.1 Responsabilidade de cada componente

| Componente | Responsabilidade principal |
|---|---|
| `StartupOrchestrator` | arranque endurecido, validações iniciais e decisão de estado de entrada |
| `CoreRuntimeController` | coordenação do ciclo de vida do módulo |
| `CoreEventInbox` | receção, ordenação e serialização do processamento de eventos |
| `CoreStateMachine` | aplicação da matriz de transições e atualização do estado global |
| `TransitionGuardEngine` | validação de pré-condições antes de cada transição |
| `BlockManager` | manutenção do vetor de bloqueios ativos e motivo dominante |
| `ModePolicyEvaluator` | restrições por modo e perfis de manutenção |
| `HeartbeatSupervisor` | liveness de módulos críticos e geração de eventos derivados |
| `GlobalStatePublisher` | publicação do estado oficial para consumo externo |
| `CriticalTransitionRecorder` | registo de transições críticas e suporte a persistência/recovery |

### 5.2 Regra obrigatória
Nenhum módulo fora do CORE pode mutar diretamente o estado global do sistema.  
Os restantes módulos só podem influenciar o CORE através de eventos e contratos definidos.

---

## 6. Contratos técnicos centrais

### 6.1 Estrutura mínima: `global_state_snapshot`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `snapshot_id` | Sim | ID do snapshot em memória/publicação |
| `state_code` | Sim | estado global canónico |
| `mode_code` | Sim | modo operacional canónico |
| `last_transition_event` | Sim | evento que originou a última transição |
| `last_transition_at_utc` | Sim | timestamp UTC da última transição |
| `readiness_class` | Sim | classe resumida de prontidão |
| `integrity_class` | Sim | classe resumida de integridade |
| `kill_active` | Sim | se existe kill ativo |
| `active_block_count` | Sim | número de bloqueios ativos |
| `dominant_block_reason` | Não | motivo dominante projetado |
| `recovery_required` | Sim | se recovery é obrigatório |

### 6.2 Estrutura mínima: `core_event_envelope`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `event_id` | Sim | identificador único |
| `event_type` | Sim | tipo de evento canónico |
| `source_module` | Sim | origem funcional/técnica |
| `timestamp_utc` | Sim | instante do evento |
| `severity` | Sim | severidade canónica |
| `correlation_id` | Recomendado | correlação entre eventos |
| `payload_schema_version` | Sim | versão do contrato |
| `payload` | Sim | payload específico |

### 6.3 Estrutura mínima: `active_block_vector`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `vector_id` | Sim | ID do vetor |
| `updated_at_utc` | Sim | última atualização |
| `blocks` | Sim | lista de bloqueios ativos |
| `dominant_block_reason` | Sim | motivo dominante calculado |
| `dominant_block_priority` | Sim | prioridade do bloqueio dominante |
| `manual_clear_required` | Sim | se existe bloqueio que exige limpeza humana |

### 6.4 Estrutura mínima de cada entrada de bloqueio: `block_entry`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `block_id` | Sim | ID do bloqueio |
| `block_code` | Sim | código canónico |
| `source_module` | Sim | origem |
| `created_at_utc` | Sim | timestamp de criação |
| `severity` | Sim | severidade |
| `reason_code` | Sim | motivo resumido |
| `reason_text` | Não | detalhe auditável |
| `manual_clear_required` | Sim | limpeza manual exigida |
| `clearable_by_recovery` | Sim | se o recovery pode ou não remover |
| `metadata` | Não | metadados adicionais |

### 6.5 Estrutura mínima: `module_heartbeat`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `module_name` | Sim | nome do módulo |
| `emitted_at_utc` | Sim | timestamp emitido pelo módulo |
| `observed_at_utc` | Sim | timestamp de receção |
| `status_code` | Sim | `OK`, `DELAYED` ou `TIMEOUT` |
| `consecutive_failures` | Sim | falhas seguidas |
| `timeout_threshold_ms` | Sim | limiar configurado |
| `details` | Não | detalhe útil de liveness |

### 6.6 Estrutura mínima: `startup_validation_result`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `startup_id` | Sim | ID do ciclo de arranque |
| `configuration_ok` | Sim | configuração válida |
| `persistence_ok` | Sim | persistência utilizável |
| `required_modules_ok` | Sim | módulos críticos mínimos disponíveis |
| `kill_active` | Sim | kill persistente ativo |
| `block_vector_loaded` | Sim | vetor de bloqueios carregado |
| `recommended_entry_state` | Sim | estado recomendado após validação |
| `operator_action_required` | Sim | se exige intervenção humana |
| `validation_notes` | Não | notas resumidas |

### 6.7 Estrutura mínima: `transition_guard_result`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `guard_result_id` | Sim | ID do resultado |
| `event_id` | Sim | evento avaliado |
| `from_state` | Sim | estado de origem |
| `requested_to_state` | Sim | destino pretendido |
| `allowed` | Sim | se a transição é permitida |
| `blocking_reason_code` | Não | motivo de rejeição |
| `required_operator_action` | Não | ação necessária para desbloqueio |
| `evaluated_at_utc` | Sim | timestamp |

### 6.8 Estrutura mínima: `core_public_state_view`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `state_code` | Sim | estado oficial |
| `mode_code` | Sim | modo oficial |
| `status_summary` | Sim | resumo legível |
| `kill_active` | Sim | kill em vigor ou não |
| `dominant_block_reason` | Não | projeção principal |
| `active_block_vector` | Sim | vetor completo |
| `readiness_class` | Sim | prontidão resumida |
| `integrity_class` | Sim | integridade resumida |
| `last_transition` | Sim | resumo da última transição |
| `critical_module_liveness` | Sim | visão resumida dos heartbeats |

### 6.9 Regra obrigatória
Estes contratos devem ser considerados a base canónica do MVP e ser refletidos semântica e estruturalmente em `SDS-110`, `SDS-120` e nos tipos partilhados futuros.

---

## 7. Arranque endurecido

### 7.1 Objetivo
Garantir que o Odin não entra em operação por estado residual, kill esquecido, persistência inconsistente ou ausência de módulos críticos.

### 7.2 Fases mínimas do arranque

1. carregar configuração e modo pretendido;
2. marcar arranque em curso na persistência;
3. ler kill flag persistente;
4. ler vetor de bloqueios persistido;
5. validar integridade do estado persistido;
6. confirmar disponibilidade mínima dos módulos críticos;
7. decidir estado de entrada seguro;
8. publicar estado inicial;
9. só depois aceitar eventos operacionais normais.

### 7.3 Regras obrigatórias
- Kill persistente ativo impede progressão para estados operacionais.
- Persistência inconsistente força fluxo conservador e pode exigir recovery.
- Arranque sem `MARKET`, `RISK` e persistência mínima não pode convergir para `READY` ou `ACTIVE`.
- `STARTUP` não pode saltar diretamente para `ACTIVE`.

---

## 8. Paragem controlada

### 8.1 Objetivo
Garantir encerramento rastreável, persistência coerente do estado final e distinção clara entre shutdown limpo e não limpo.

### 8.2 Fases mínimas

1. aceitar comando de stop ou shutdown sistémico;
2. congelar novas transições operacionais não críticas;
3. persistir snapshot final do CORE;
4. marcar encerramento limpo;
5. publicar estado de saída;
6. terminar ciclo de runtime.

### 8.3 Regra obrigatória
Falha na persistência do encerramento limpo deve ser registada como incidente técnico e tratada no próximo arranque como potencial shutdown não limpo.

---

## 9. Modelo técnico de processamento de eventos

### 9.1 Objetivo
Garantir que eventos internos e externos convergem para mutações determinísticas do estado global.

### 9.2 Pipeline mínimo

1. receção do evento;
2. validação estrutural do envelope;
3. classificação por precedência;
4. consulta do estado atual e do vetor de bloqueios;
5. avaliação de guards;
6. cálculo do destino;
7. aplicação da transição;
8. atualização do vetor de bloqueios, se aplicável;
9. persistência de transição crítica, se aplicável;
10. publicação do novo estado oficial.

### 9.3 Regras obrigatórias
- Eventos inválidos devem ser rejeitados explicitamente.
- Eventos críticos não podem ser silenciosamente descartados.
- A publicação do estado oficial deve refletir exatamente o resultado consolidado da transição.

---

## 10. Serialização e concorrência

### 10.1 Princípio base
No MVP do Odin, o CORE deverá operar com **um único pipeline serial de mutação de estado**.

### 10.2 Estratégia recomendada
- `CoreEventInbox` com fila ordenada;
- um único consumidor lógico por instância do CORE;
- precedência de eventos aplicada antes da mutação;
- queries e leitura do `core_public_state_view` separadas do pipeline de escrita.

### 10.3 Regra obrigatória
Não é permitido processar em paralelo dois eventos que possam alterar estado global, vetor de bloqueios, modo operacional ou classe de integridade.

### 10.4 Implicação técnica
Escalabilidade horizontal, distribuição de estado e multi-writer ficam fora do âmbito do MVP.

---

## 11. State machine do CORE

### 11.1 Estados canónicos suportados
- `ST-00 OFFLINE`
- `ST-10 STARTUP`
- `ST-20 IDLE`
- `ST-30 MONITORING`
- `ST-40 READY`
- `ST-50 ACTIVE`
- `ST-60 PAUSED`
- `ST-70 BLOCKED_RISK`
- `ST-80 BLOCKED_FAULT`
- `ST-90 ERROR`
- `ST-100 RECOVERY`
- `ST-110 TRAINING`
- `ST-120 MAINTENANCE`

### 11.2 Regras mínimas de progressão
- `OFFLINE -> STARTUP` por `EV-START`
- `STARTUP -> IDLE` só com validação mínima concluída
- `IDLE -> MONITORING` quando o runtime estiver estável
- `MONITORING -> READY` só com MARKET e RISK compatíveis
- `READY -> ACTIVE` depende de modo compatível e ausência de bloqueios
- `ACTIVE -> PAUSED` por pausa explícita ou política conservadora
- `ACTIVE -> BLOCKED_RISK` por evento de risco dominante
- `ACTIVE -> BLOCKED_FAULT` por falha, heartbeat timeout ou divergência crítica
- `ANY -> MAINTENANCE` só por entrada explícita autorizada
- `ANY -> RECOVERY` quando existir necessidade formal de reconstrução

### 11.3 Transições proibidas
- `OFFLINE -> ACTIVE`
- `STARTUP -> ACTIVE`
- `RECOVERY -> ACTIVE`
- `BLOCKED_RISK -> ACTIVE` sem limpeza formal do bloqueio
- `BLOCKED_FAULT -> ACTIVE` sem recuperação validada
- `ERROR -> ACTIVE`

### 11.4 Regra obrigatória
O CORE deve rejeitar explicitamente qualquer transição não prevista ou proibida e gerar evento técnico rastreável.

---

## 12. Guards de transição

### 12.1 Objetivo
Garantir que o destino de uma transição é validado contra estado, modo, bloqueios, liveness, persistência e integridade.

### 12.2 Guards mínimos
- `KillInactiveGuard`
- `PersistenceConsistentGuard`
- `RequiredModulesAliveGuard`
- `NoHigherPriorityBlockGuard`
- `ModeCompatibilityGuard`
- `RecoveryExitGuard`
- `MaintenanceProfileGuard`
- `StartupValidationGuard`

### 12.3 Regras obrigatórias
- Guards devem ser determinísticos para os mesmos inputs.
- Resultado de guard deve ser auditável.
- Falha de guard crítico deve resultar em negação conservadora.
- Saída de recovery e desbloqueio de falha exigem guards próprios.

---

## 13. Gestão do vetor de bloqueios

### 13.1 Objetivo
Manter visão completa e não ambígua de todas as razões ativas que limitam ou proíbem a operação.

### 13.2 Responsabilidades do `BlockManager`
- adicionar bloqueios novos;
- atualizar bloqueios existentes;
- remover bloqueios autorizadamente;
- calcular motivo dominante;
- distinguir bloqueios automáticos de bloqueios com limpeza manual obrigatória;
- publicar vetor completo ao `GlobalStatePublisher`;
- persistir snapshots críticos via `PersistentStateStore`.

### 13.3 Hierarquia mínima recomendada
Da maior para a menor precedência:

1. kill ativo
2. bloqueio por falha/integridade
3. bloqueio por recovery pendente
4. bloqueio manual
5. bloqueio por risco
6. restrição por manutenção
7. restrição operacional não bloqueante

### 13.4 Regras obrigatórias
- O motivo dominante não substitui o vetor completo.
- Bloqueio manual não sai automaticamente.
- Kill persistente não pode ser limpo por recovery.
- A remoção de um bloqueio não deve apagar histórico auditável da sua existência.

---

## 14. Gestão de modos operacionais

### 14.1 Objetivo
Separar rigorosamente o modo operacional do estado global e aplicar política adequada a cada combinação.

### 14.2 Modos suportados
- `MD-10 OBSERVATION`
- `MD-20 DEMO`
- `MD-30 REAL`
- `MD-40 TRAINING`
- `MD-50 MAINTENANCE`

### 14.3 Responsabilidades do `ModePolicyEvaluator`
- validar pedidos de mudança de modo;
- aplicar envelopes mínimos por modo;
- impedir progressão incompatível com o modo;
- forçar restrições adicionais em `REAL` e `MAINTENANCE`.

### 14.4 Regras obrigatórias
- Mudança para `REAL` exige pré-condições reforçadas.
- `MAINTENANCE` deve exigir perfil explícito de saída.
- `TRAINING` e `MAINTENANCE` não podem ser confundidos.
- O modo não altera sozinho o estado global sem evento e guard compatíveis.

---

## 15. Supervisão de heartbeat e liveness

### 15.1 Objetivo
Detetar cegueira modular antes que ela se transforme em operação insegura.

### 15.2 Módulos críticos mínimos
- `MARKET`
- `RISK`
- `EXEC` quando existir pipeline de execução ativo

### 15.3 Comportamentos mínimos do `HeartbeatSupervisor`
- registar heartbeat válido;
- detetar atraso;
- detetar timeout;
- emitir `EV-HB-DELAYED` ou `EV-HB-TIMEOUT`;
- refletir impacto no estado global conforme severidade.

### 15.4 Regras obrigatórias
- Silêncio de módulo crítico nunca deve ser interpretado como saudável.
- Timeout de módulo crítico deve gerar bloqueio conservador ou regressão de estado.
- Heartbeat válido não limpa, por si só, bloqueios manuais, kill ou recovery pendente.

---

## 16. Publicação do estado global

### 16.1 Objetivo
Expor ao sistema e ao operador uma visão oficial, consolidada e estável do estado do Odin.

### 16.2 Responsabilidades do `GlobalStatePublisher`
- publicar `core_public_state_view`;
- incluir vetor completo de bloqueios ativos;
- incluir resumo de liveness crítico;
- manter semântica estável entre publicações;
- produzir eventos de transição relevantes para observabilidade.

### 16.3 Regras obrigatórias
- O DASH e módulos observacionais devem consumir o estado publicado pelo CORE, não recomputá-lo.
- A publicação deve acontecer após a consolidação da transição.
- Campos essenciais não podem depender de parsing textual de logs.

---

## 17. Integração com persistência

### 17.1 Dependência principal
O CORE depende de `PersistentStateStore` conforme especificado em SDS-110.

### 17.2 Escritas mínimas disparadas pelo CORE
- snapshot crítico após transição de alta severidade;
- kill flag persistente quando kill entra ou sai;
- vetor de bloqueios em mudanças relevantes;
- shutdown marker e startup marker;
- recovery snapshot quando necessário.

### 17.3 Regras obrigatórias
- Falha em escrita crítica deve ser tratada como incidente técnico.
- Persistência não deve alterar semântica de estado; apenas suportá-la.
- O CORE deve distinguir claramente estado em memória, estado publicado e estado persistido.

---

## 18. Integração com interfaces

### 18.1 Dependência principal
Os contratos de interface física/lógica do CORE são fechados em SDS-120.

### 18.2 Regra obrigatória
SDS-100 define a semântica do núcleo; SDS-120 define como essa semântica é transportada entre módulos.  
Nenhum contrato novo entre módulos críticos deve surgir fora desta dupla SDS-100/SDS-120.

### 18.3 Interface com memória auxiliar
O CORE pode publicar contexto não crítico para indexação ou análise histórica, mas não deve consumir memória auxiliar como autoridade de:
- `global_state`
- `current_mode`
- `active_block_vector`
- `kill_active`
- `recovery_required`

### 18.4 Regras obrigatórias
- indisponibilidade da memória auxiliar não pode alterar a semântica do CORE;
- o CORE pode expor referências auditáveis para memória auxiliar, mas não deve depender delas para transição de estado;
- qualquer integração com sidecar de memória deve ser estritamente observacional ou advisory.

---

## 19. Fail-safe e regras de falha

### 19.1 Falhas mínimas a tratar
- evento inválido;
- transição proibida;
- inconsistência de persistência;
- ausência de módulo crítico;
- heartbeat timeout;
- kill ativo;
- tentativa de limpeza indevida de bloqueio;
- saída inválida de recovery;
- falha de publicação do estado global.

### 19.2 Regras obrigatórias
- Em caso de dúvida, o CORE deve preferir restringir ou bloquear.
- Falha interna do CORE não pode resultar em promoção silenciosa de estado.
- Recovery exigido deve prevalecer sobre tentativa otimista de retoma.

---

## 20. Observabilidade e logging técnico

### 20.1 Eventos mínimos a registar
- arranque iniciado e concluído;
- resultado da validação de arranque;
- mudança de estado;
- mudança de modo;
- adição/remoção de bloqueio;
- timeout de heartbeat;
- tentativa de transição rejeitada;
- entrada e saída de recovery;
- falhas de persistência crítica.

### 20.2 Campos mínimos
- `event_id`
- `event_type`
- `source_module`
- `state_before`
- `state_after`
- `mode_code`
- `dominant_block_reason`
- `kill_active`
- `correlation_id`
- `timestamp_utc`

### 20.3 Regra obrigatória
Logs críticos do CORE devem ser tratáveis como append-only ao nível funcional, mesmo que a implementação use backend diferente.

---

## 21. Configuração mínima obrigatória

| Parâmetro | Finalidade |
|---|---|
| `core.startup_timeout_ms` | limite do arranque endurecido |
| `core.event_queue_max_size` | limite da fila de eventos |
| `core.required_modules` | lista de módulos críticos mínimos |
| `core.heartbeat_timeout_ms` | timeout base de liveness |
| `core.heartbeat_grace_count` | tolerância antes do timeout final |
| `core.allow_real_mode` | gate explícito para `MD-30` |
| `core.recovery_required_on_unclean_shutdown` | política de restart conservador |
| `core.persist_on_critical_transition` | política de escrita crítica |

---

## 22. Estrutura técnica recomendada de código

```text
odin/
├── src/
│   ├── core/
│   │   ├── runtime/
│   │   ├── startup/
│   │   ├── state_machine/
│   │   ├── guards/
│   │   ├── blocks/
│   │   ├── modes/
│   │   ├── heartbeats/
│   │   ├── publisher/
│   │   ├── events/
│   │   └── audit/
│   ├── shared/
│   │   ├── models/
│   │   ├── enums/
│   │   ├── contracts/
│   │   └── logging/
│   ├── persistence/
│   └── config/
```

---

## 23. Testes técnicos mínimos

### 23.1 Unit tests
- aceitação e rejeição de transições;
- cálculo do estado de destino;
- precedência de eventos;
- cálculo do motivo dominante do vetor de bloqueios;
- guards de arranque;
- guards de saída de recovery;
- decisão de timeout de heartbeat.

### 23.2 Integration tests
- arranque limpo sem bloqueios;
- arranque com kill persistente;
- restart com shutdown não limpo a convergir para recovery;
- perda de heartbeat de `MARKET` e `RISK`;
- bloqueio manual a impedir retoma automática;
- mudança de modo com política incompatível;
- publicação correta do `core_public_state_view`.

### 23.3 Fault-injection tests
- persistência inconsistente no arranque;
- falha de escrita em transição crítica;
- receção de evento com schema inválido;
- timeout simultâneo de módulos críticos;
- tentativa de saída de recovery sem validação suficiente.

---

## 24. Critérios de aceitação

O SDS-100 — CORE será considerado tecnicamente suficiente quando:

1. a state machine puder ser implementada sem ambiguidades graves;
2. o pipeline de arranque endurecido estiver claramente definido;
3. a serialização de eventos impedir mutação concorrente de estado no MVP;
4. o vetor completo de bloqueios estiver modelado e com precedência explícita;
5. a gestão de heartbeat dos módulos críticos estiver fechada;
6. a semântica do estado publicado pelo CORE estiver estabilizada;
7. persistência, interfaces e recovery dependerem do CORE sem pressupostos implícitos;
8. os testes mínimos cobrirem transições, restart e fail-safe.

---

## 25. Dependências e próximos documentos

### 25.1 Dependências principais
- `docs/fsd/ODIN_FSD_Consolidado_v0_5.md`
- `docs/models/ODIN-CORE-STATE-AND-EVENT-MODEL.md`
- `docs/traceability/ODIN-TRACEABILITY-MATRIX.md`

### 25.2 Documentos ligados diretamente
- SDS-110 — CORE-PERSISTENCE
- SDS-120 — CORE-INTERFACES
- SDS-700 — RECOVERY

### 25.3 Próximos artefactos recomendados
- tipos partilhados em `src/shared/contracts/`
- testes de transição do CORE
- harness de restart/recovery

---

## 26. Conclusão

O SDS-100 fecha a lacuna central da arquitetura documental do Odin: transforma o CORE de conceito funcional e modelo intermédio numa peça técnica implementável.

É este documento que permite começar F1 com disciplina:
- um núcleo serializado;
- um estado global único;
- guards formais;
- bloqueios completos;
- arranque e retoma conservadores;
- e um contrato oficial de estado para o resto do sistema.
