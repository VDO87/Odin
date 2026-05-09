# SDS-600 — DASH
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Arquitetura técnica do dashboard operacional, observabilidade, controlo manual autorizado, alarmes, histórico, exportação de logs e interface assistida.

---

## 1. Finalidade do documento

Este documento define a especificação técnica do módulo **DASH** do Odin.

Se o FSD-600 define **o que** o dashboard deve permitir observar e controlar, este SDS-600 define **como** a camada de supervisão humana deve ser estruturada tecnicamente para:

- refletir o estado oficial do sistema;
- expor informação operacional sem contradições;
- permitir ações autorizadas sem contornar o CORE;
- apresentar alarmes e bloqueios de forma inequívoca;
- disponibilizar histórico e logs de forma utilizável;
- suportar uma interface assistida limitada ao domínio do Odin.

O DASH não é o cérebro do sistema. É a sua **superfície operacional**.  
Por isso, a sua implementação tem de ser clara, segura, auditável e rigidamente alinhada com os contratos publicados pelos módulos centrais.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- arquitetura lógica do dashboard;
- composição técnica das vistas e painéis;
- modelo de leitura do estado global e dos módulos;
- contratos de controlo manual;
- modelo de alarmes e notificações operacionais;
- histórico operacional e consulta de logs;
- exportação funcional de logs;
- gestão técnica de permissões de interface;
- interface assistida orientada ao domínio;
- integração com CORE, MARKET, DECISION, RISK, EXEC, RECOVERY e LEARN.

### 2.2 Excluído
Este documento não inclui:
- design visual final pixel-perfect;
- escolha final de framework frontend;
- detalhe de deployment web/local;
- implementação do motor de IA da interface assistida;
- APIs externas não relacionadas com o dashboard.

---

## 3. Objetivos técnicos

O módulo DASH deverá garantir, no mínimo:

1. **Fonte de verdade coerente**  
   O dashboard deve consumir e apresentar o estado oficial publicado pelos módulos, sobretudo pelo CORE.

2. **Separação de observação e controlo**  
   A arquitetura deve impedir mistura perigosa entre vistas informativas e ações de controlo.

3. **Segurança operacional de interface**  
   Ações críticas devem ser autorizadas, auditadas e condicionadas pelo estado do sistema.

4. **Observabilidade operacional útil**  
   O operador deve conseguir perceber rapidamente:
   - porque o sistema está bloqueado;
   - em que estado está;
   - o que aconteceu recentemente;
   - que ação pode ou não pode executar.

5. **Compatibilidade com modo Real**  
   Em modo Real, o dashboard deve endurecer confirmações, alarmes e visibilidade de risco.

6. **Não inferir lógica invisível**  
   O dashboard não deve recalcular lógica de decisão, risco ou estado. Deve refletir a publicada oficialmente.

7. **Consulta assistida com memória delimitada**  
   A interface assistida pode recorrer a memória auxiliar para recall histórico, desde que identifique a origem e nunca substitua o estado oficial publicado.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-600 — DASH
- FSD consolidado v0.5
- SDS-100 — CORE
- SDS-120 — CORE-INTERFACES
- SDS-200 — MARKET
- SDS-300 — DECISION
- SDS-400 — RISK
- SDS-500 — EXEC
- SDS-700 — RECOVERY
- SDS-800 — LEARN
- ODIN-TRACEABILITY-MATRIX

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| O dashboard deve refletir o estado oficial do CORE | FSD-600 | `GlobalStateViewModel` + subscrição do CORE |
| O dashboard deve separar observação de controlo | FSD-600 | `ReadViews` e `ControlActions` segregadas |
| O dashboard deve mostrar bloqueios e alarmes críticos | FSD-600 / v0.4 | `AlarmCenter` + `BlockVectorPanel` |
| O dashboard deve só permitir ações compatíveis com o estado | FSD-600 | `ActionAvailabilityResolver` |
| O dashboard deve exportar logs | FSD-600 | `LogQueryService` + `ExportService` |
| O dashboard deve suportar interface assistida limitada | FSD-600 | `AssistedQueryLayer` |

---

## 5. Arquitetura lógica do DASH

O DASH deverá ser decomposto, no mínimo, nos seguintes componentes técnicos.

### 5.1 Componentes principais

| Componente | Responsabilidade técnica |
|---|---|
| `DashboardShell` | estrutura principal da aplicação de dashboard |
| `GlobalStateViewModel` | projeção do estado global oficial |
| `ModuleStateAggregator` | agregação das visões resumidas dos módulos |
| `ActionAvailabilityResolver` | cálculo das ações permitidas para a interface |
| `AlarmCenter` | gestão de alarmes, avisos e severidades |
| `ControlActionDispatcher` | despacho de comandos manuais autorizados |
| `OperationalHistoryView` | histórico operacional resumido |
| `LogQueryService` | consulta estruturada de logs |
| `ExportService` | exportação de logs/subconjuntos |
| `AssistedQueryLayer` | perguntas orientadas e respostas limitadas ao domínio |
| `MemoryAssistedSearchAdapter` | consulta memória auxiliar para recall histórico não autoritativo |
| `PermissionResolver` | validação de permissões por perfil de interface |
| `DashboardAuditLogger` | logging técnico das ações da interface |

---

## 6. Modelo técnico do dashboard

### 6.1 Áreas técnicas obrigatórias
O dashboard deverá ser organizado, no mínimo, nas seguintes áreas lógicas:

1. `GlobalStatusArea`
2. `OperationalObservationArea`
3. `ManualControlArea`
4. `AlarmAndCriticalEventsArea`
5. `OperationalHistoryArea`
6. `LogsAndExportArea`
7. `AssistedInteractionArea`

### 6.2 Regra obrigatória
`ManualControlArea` não deve partilhar fluxo de ação com vistas puramente informativas.

---

## 7. Modelo de leitura do estado global

### 7.1 Fonte de dados
O estado global apresentado pelo dashboard deve ser consumido do contrato publicado pelo CORE.

### 7.2 Estrutura mínima: `dashboard_global_state_model`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `global_state` | Sim | estado global oficial |
| `current_mode` | Sim | modo atual |
| `dashboard_profile` | Sim | profile de superfície ativa (`lite`, `standard`, `full`) |
| `state_updated_at_utc` | Sim | timestamp da última transição |
| `dominant_block_reason` | Não | motivo dominante |
| `active_block_vector` | Recomendado | vetor completo de bloqueios |
| `available_actions` | Sim | ações permitidas |
| `critical_flags` | Recomendado | kill, recovery, divergence, etc. |
| `heartbeat_health_summary` | Recomendado | saúde de módulos críticos |
| `operation_focus` | Recomendado | resumo operacional para `DASH-lite` |

### 7.3 Regra obrigatória
Se o dashboard não tiver confirmação recente do `global_state`, deve apresentar estado de desconfiança na interface, e não fingir atualização.

---

## 8. Modelo de observação operacional por módulo

O dashboard deverá manter view models separados por domínio.

### 8.1 `market_panel_model`

| Campo | Obrigatório |
|---|---|
| `market_state` | Sim |
| `context_class` | Sim |
| `feed_integrity_state` | Sim |
| `session_ref` | Recomendado |
| `last_valid_update_utc` | Sim |
| `spread_state` | Recomendado |
| `news_guard_state` | Recomendado |

### 8.2 `decision_panel_model`

| Campo | Obrigatório |
|---|---|
| `decision_state` | Sim |
| `decision_output` | Sim |
| `decision_cycle_id` | Recomendado |
| `winner_hypothesis_summary` | Não |
| `score_summary` | Não |
| `reason_summary` | Sim |
| `blocked_by_external` | Sim |

### 8.3 `risk_panel_model`

| Campo | Obrigatório |
|---|---|
| `risk_state` | Sim |
| `kill_active` | Sim |
| `dominant_risk_reason` | Sim |
| `restriction_flags` | Recomendado |
| `cooldown_state` | Recomendado |
| `limit_summary` | Recomendado |

### 8.4 `exec_panel_model`

| Campo | Obrigatório |
|---|---|
| `execution_state` | Sim |
| `last_intent_id` | Não |
| `last_result_summary` | Recomendado |
| `pending_state` | Recomendado |
| `divergence_active` | Sim |
| `slippage_rejection_state` | Recomendado |

### 8.5 `recovery_panel_model`

| Campo | Obrigatório |
|---|---|
| `recovery_state` | Sim |
| `incident_type` | Não |
| `recovery_result` | Não |
| `manual_intervention_required` | Sim |
| `reconciliation_confidence` | Recomendado |

### 8.6 `learn_panel_model`

| Campo | Obrigatório |
|---|---|
| `learn_state` | Sim |
| `active_version` | Recomendado |
| `pending_proposal` | Não |
| `approval_status` | Recomendado |
| `last_change_summary` | Recomendado |
| `rollback_state` | Recomendado |
| `learn_shadow_audit` | Recomendado |
| `learn_operational_hints` | Recomendado |

Regra de profile:
- no profile `lite`, o `DASH` não deve expor `learn_panel_model`;
- no profile `standard`, a presença do `LEARN` continua opcional e dependente do runtime;
- no profile `full`, o painel LEARN pode ser projetado integralmente.

### 8.7 `learn_shadow_audit_model`

| Campo | Obrigatório |
|---|---|
| `shadow_required` | Sim |
| `shadow_status` | Sim |
| `shadow_session_id` | Não |
| `evaluation_scope` | Não |
| `started_at_utc` | Não |
| `ended_at_utc` | Não |
| `promotion_recommendation` | Não |

### 8.8 `learn_query_results`

O payload de observação do corte F7 pode expor `learn_query_results` com queries explícitas do LEARN.

Chaves mínimas suportadas no estado atual:
- `LEARN_QUERY_PROPOSAL`
- `LEARN_QUERY_APPROVAL`
- `LEARN_QUERY_SHADOW_AUDIT`
- `LEARN_QUERY_SHADOW_RECOMMENDATION`
- `LEARN_QUERY_ACTIVE_VERSION`
- `LEARN_QUERY_ROLLBACK_AUDIT`

Regra obrigatória:
- queries LEARN explícitas devem ser hidratadas a partir do `runtime` e do `LearningOrchestrator`, e não recalculadas localmente pelo dashboard.
- no profile `lite`, `learn_query_results` deve ser omitido.

### 8.9 `dashboard_operation_focus`

Para o corte de operação inicial em hardware limitado, o `DASH-lite` pode expor um resumo operacional curto:

| Campo | Obrigatório |
|---|---|
| `execution_gate` | Sim |
| `next_actions` | Sim |
| `resume_allowed` | Sim |
| `active_block_count` | Sim |
| `dominant_block_reason` | Não |
| `state_code` | Sim |
| `mode_code` | Sim |
| `dashboard_surface` | Sim |
| `last_execution` | Recomendado |
| `market_runtime` | Recomendado |

Regra obrigatória:
- `dashboard_operation_focus` deve ser derivado do estado oficial do `CORE` e, quando existir, do último registo do execution ledger persistido.
- quando o runtime expuser estado operacional do `MARKET`, `market_runtime` deve refletir o profile ativo e as restrições efetivas do gate de ingestão.
- no corte atual, `market_runtime` deve conseguir expor pelo menos `execution_profile`, `market_profile`, `instrument_scope`, `feed_scope`, `max_instruments`, `max_feeds`, `news_guard_enabled`, `spread_guard_enabled`, `heavy_enrichment_enabled`, `active_restrictions`, `last_gate_status`, `last_rejection_reason`, `last_instrument_id`, `last_feed_id` e `applied_restrictions`.
- `last_execution` deve ser hidratado a partir do estado persistido (`read_latest_execution_ledger_record()`), não por cache local efémera do dashboard.
- `market_runtime` deve ser hidratado a partir do runtime (`get_market_runtime_status()` + serialização `to_dict()`), não reconstruído fora do pipeline oficial.

---

## 9. Alarmes e eventos críticos

### 9.1 Objetivo
Disponibilizar uma camada única para eventos que exigem atenção prioritária.

### 9.2 Estrutura mínima: `dashboard_alarm_item`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `alarm_id` | Sim | ID do alarme |
| `severity` | Sim | severidade |
| `alarm_type` | Sim | tipo lógico |
| `source_module` | Sim | origem |
| `created_at_utc` | Sim | timestamp |
| `is_active` | Sim | ativo/inativo |
| `title` | Sim | título curto |
| `summary` | Sim | resumo técnico-operacional |
| `linked_state_ref` | Não | referência a estado/ciclo/intent |

### 9.3 Fontes mínimas de alarme
- kill ativo;
- bloqueio manual;
- bloqueio por risco;
- bloqueio por falha;
- heartbeat timeout;
- mercado hostil;
- divergência de execução;
- recovery inconclusivo;
- intervenção humana obrigatória;
- slippage rejeitado;
- intenção expirada.

### 9.4 Regras obrigatórias
- `CRITICAL` deve aparecer sempre acima de `WARN`.
- Alarmes resolvidos não devem continuar visíveis como ativos.
- O dashboard deve suportar distinção entre:
  - `active_alarm`
  - `historical_alarm`
  - `acknowledged_alarm` (se esta função existir)

---

## 10. Centro de bloqueios

### 10.1 Objetivo
Expor não só o motivo dominante, mas o conjunto dos bloqueios ativos.

### 10.2 Estrutura mínima: `block_vector_panel_model`

| Campo | Obrigatório |
|---|---|
| `dominant_block_reason` | Sim |
| `active_block_vector` | Sim |
| `block_count` | Sim |
| `has_manual_block` | Sim |
| `has_kill_block` | Sim |
| `has_fault_block` | Sim |

### 10.3 Regra obrigatória
O operador deve conseguir perceber rapidamente:
- que bloqueio domina;
- que outros bloqueios coexistem;
- qual o que exige limpeza manual.

---

## 11. Área de controlo manual

### 11.1 Objetivo
Emitir comandos para o CORE sem contornar o modelo de permissões.

### 11.2 Ações mínimas suportadas
- `START`
- `STOP`
- `PAUSE`
- `RESUME`
- `MODE_CHANGE`
- `MAINTENANCE_ENTER`
- `MAINTENANCE_EXIT`
- `REQUEST_RECOVERY_VALIDATION`
- `EXPORT_LOGS`
- `LEARN_ACTION_REVIEW_APPROVAL`
- `LEARN_ACTION_EVALUATE_PROMOTION`
- `LEARN_ACTION_START_SHADOW`
- `LEARN_ACTION_COMPLETE_SHADOW`
- `LEARN_ACTION_ACTIVATE_PROPOSAL`
- `LEARN_ACTION_TRIGGER_ROLLBACK`

Regra de profile:
- no profile `lite`, ações LEARN não devem ser disponibilizadas;
- se um operador tentar forçar uma ação LEARN num profile que a desative, a rejeição deve ser explícita (`feature_disabled_for_profile`).

### 11.3 Estrutura mínima: `dashboard_control_action_request`

| Campo | Obrigatório |
|---|---|
| `action_id` | Sim |
| `action_type` | Sim |
| `requested_by` | Sim |
| `requested_at_utc` | Sim |
| `authorization_context` | Sim |
| `reason_text` | Recomendado |
| `maintenance_profile` | Obrigatório quando aplicável |

### 11.4 Regra obrigatória
O DASH não executa a ação localmente.  
Despacha o pedido para o CORE, que:
- valida;
- aceita ou rejeita;
- devolve resultado.

Regra adicional do corte atual:
- `MAINTENANCE_ENTER` sem `maintenance_profile` deve ser rejeitado com `maintenance_profile_required`.

No corte F7, ações LEARN podem devolver `learn_action_result` no payload da resposta com:
- `accepted`
- `blocking_reason_code`
- `blocking_summary`
- artefactos relevantes de approval, shadow, activation ou rollback, quando existirem

---

## 12. Resolvedor de disponibilidade de ações

### 12.1 Objetivo
Calcular que ações podem ser mostradas ou permitidas no momento.

### 12.2 Entradas mínimas
- `global_state`
- `current_mode`
- `dashboard_profile`
- `active_block_vector`
- `permission_profile`
- `kill_active`
- `manual_block_active`
- `recovery_state`
- `learn_state_view`

### 12.3 Saídas mínimas
- `available_actions`
- `forbidden_actions`
- `confirmation_required_actions`
- `maintenance_profile_required`
- `resume_allowed`

### 12.4 Regras obrigatórias
- uma ação proibida não deve aparecer como clicável;
- ações críticas devem exigir confirmação adicional;
- `RESUME` não pode ser disponibilizado se existir bloqueio manual por limpar ou kill ativo;
- entrada em manutenção deve exigir seleção de perfil.
- disponibilidade das ações LEARN deve respeitar `approval_status`, exigência/estado de shadow, `promotion_recommendation` e existência de versão ativa.
- no profile `lite`, o resolvedor deve operar sem superfície LEARN e sem queries LEARN.

---

## 13. Modelo técnico de permissões

### 13.1 Perfis mínimos

| Perfil | Capacidades mínimas |
|---|---|
| `viewer` | observação, histórico, logs limitados |
| `operator` | observação + start/stop/pause/resume controlados |
| `supervisor` | operator + mudança de modo + kill/controlo reforçado |
| `maintenance_admin` | supervisor + manutenção + recovery técnico + gestão expandida |

### 13.2 Estrutura mínima: `dashboard_permission_context`

| Campo | Obrigatório |
|---|---|
| `principal_id` | Sim |
| `role` | Sim |
| `granted_actions` | Sim |
| `restricted_actions` | Sim |
| `session_started_at_utc` | Recomendado |

### 13.3 Regras obrigatórias
- permissões devem ser verificadas antes do envio do comando;
- permissões da interface não substituem validação final do CORE;
- toda ação crítica deve ser auditável com `requested_by`.

---

## 14. Histórico operacional

### 14.1 Objetivo
Dar ao operador uma timeline resumida sem exigir leitura de logs brutos.

### 14.2 Estrutura mínima: `operational_history_item`

| Campo | Obrigatório |
|---|---|
| `history_id` | Sim |
| `timestamp_utc` | Sim |
| `module` | Sim |
| `event_type` | Sim |
| `severity` | Sim |
| `summary` | Sim |
| `linked_ref` | Não |

### 14.3 Categorias mínimas filtráveis
- transições de estado;
- alterações de modo;
- bloqueios;
- eventos de risco;
- eventos de execução;
- recovery;
- aprendizagem;
- ações humanas.

---

## 15. Consulta de logs

### 15.1 Objetivo
Permitir acesso operacional a logs estruturados sem exposição desnecessária de internals.

### 15.2 Estrutura mínima de query: `log_query_request`

| Campo | Obrigatório |
|---|---|
| `requested_by` | Sim |
| `requested_at_utc` | Sim |
| `time_from_utc` | Recomendado |
| `time_to_utc` | Recomendado |
| `modules` | Não |
| `severity_filter` | Não |
| `event_types` | Não |
| `correlation_id` | Não |
| `limit` | Recomendado |

### 15.3 Regras obrigatórias
- logs críticos devem ser consultáveis por módulo, severidade e janela temporal;
- consultas não devem poder alterar logs;
- o sistema deve tratar logs críticos como append-only ao nível funcional.

---

## 16. Exportação de logs

### 16.1 Objetivo
Permitir exportação estruturada de logs para diagnóstico e auditoria.

### 16.2 Estrutura mínima: `log_export_request`

| Campo | Obrigatório |
|---|---|
| `requested_by` | Sim |
| `requested_at_utc` | Sim |
| `query_ref` | Sim |
| `export_format` | Sim |
| `reason_text` | Recomendado |

### 16.3 Regras obrigatórias
- a exportação deve ser auditada;
- a exportação deve preservar a ordem temporal básica;
- a exportação deve respeitar permissões do perfil;
- exportação não pode bloquear o funcionamento normal do CORE.

---

## 17. Interface assistida

### 17.1 Objetivo
Permitir perguntas orientadas ao estado operacional do Odin sem abrir porta a controlo textual livre perigoso.

### 17.2 Tipos mínimos de query assistida
- estado atual do Odin;
- motivo de bloqueio;
- última decisão;
- motivo de não operação;
- estado do risco;
- divergência de execução;
- incidente/recovery pendente;
- últimos eventos relevantes.

### 17.3 Estrutura mínima: `assisted_query_request`

| Campo | Obrigatório |
|---|---|
| `query_id` | Sim |
| `requested_by` | Sim |
| `requested_at_utc` | Sim |
| `query_type` | Sim |
| `query_payload` | Não |

### 17.4 Estrutura mínima: `assisted_query_response`

| Campo | Obrigatório |
|---|---|
| `query_id` | Sim |
| `generated_at_utc` | Sim |
| `response_type` | Sim |
| `answer_text` | Sim |
| `state_refs` | Recomendado |
| `confidence_scope` | Recomendado |

### 17.5 Regras obrigatórias
- a interface assistida só responde dentro do domínio autorizado;
- não deve produzir comandos operacionais livres;
- respostas devem basear-se no estado oficial e em dados publicados pelos módulos;
- queries assistidas devem ser auditáveis.

---

## 18. Fluxo técnico de atualização do dashboard

### 18.1 Estratégia recomendada
O dashboard deverá consumir eventos e/ou estados publicados de forma reativa, com apoio de cache local de leitura.

### 18.2 Componentes recomendados
- `state_subscription_layer`
- `view_model_store`
- `action_dispatcher`
- `alarm_projection_service`

### 18.3 Regra obrigatória
O dashboard não deve recomputar lógica crítica que pertença ao CORE, RISK ou DECISION.

No corte F7, `project_state(...)` deve receber `runtime` quando disponível para:
- resolver o `LearningOrchestrator`;
- hidratar `learn_query_results`;
- refletir bloqueios e hints operacionais do LEARN sem duplicar regras fora do domínio.

---

## 19. Timeout e degradação da interface

### 19.1 Regra
A indisponibilidade do dashboard não deve degradar a segurança operacional do sistema.

### 19.2 Comportamento esperado
- se o DASH perder ligação aos publishers, deve mostrar estado de ligação degradada;
- não deve continuar a mostrar estado antigo como se fosse atual;
- o CORE continua a operar com as suas regras mesmo que a UI falhe.

---

## 20. Logging técnico do DASH

### 20.1 Eventos mínimos a registar
- abertura de sessão de dashboard;
- comandos manuais emitidos;
- rejeição de ação por falta de permissão;
- exportação de logs;
- queries assistidas;
- falha de carregamento de estado crítico;
- mudança de perfil ou contexto de autorização, quando aplicável.

### 20.2 Campos mínimos
- `timestamp_utc`
- `principal_id`
- `action_or_query_type`
- `result_state`
- `severity`
- `correlation_id` (recomendado)
- `reason_summary`

---

## 21. Estrutura técnica recomendada de código

```text
odin/
├── src/
│   ├── dash/
│   │   ├── shell/
│   │   ├── state_views/
│   │   ├── module_panels/
│   │   ├── alarms/
│   │   ├── controls/
│   │   ├── permissions/
│   │   ├── history/
│   │   ├── logs/
│   │   ├── export/
│   │   ├── assisted/
│   │   └── audit/
│   ├── shared/
│   │   ├── models/
│   │   ├── enums/
│   │   ├── logging/
│   │   └── utils/
│   └── config/
```

---

## 22. Testes técnicos mínimos

### 22.1 Unit tests
- resolução de ações disponíveis;
- cálculo de permissões por perfil;
- transformação de estado publicado em view model;
- classificação e ordenação de alarmes;
- queries assistidas válidas/inválidas.

### 22.2 Integration tests
- leitura do estado global do CORE;
- receção de bloqueio de risco;
- receção de kill ativo;
- receção de divergência de execução;
- entrada em manutenção com perfil explícito;
- exportação de logs;
- consulta assistida do motivo de bloqueio;
- dispatch de ações LEARN válidas/inválidas;
- projeção LEARN com shadow pendente, shadow em curso, recommendation bloqueante e rollback.

### 22.3 Fault-injection tests
- perda de ligação ao publisher do CORE;
- comando enviado sem autorização;
- dashboard com estado stale;
- alarme crítico duplicado ou contraditório;
- query assistida fora do domínio permitido.

---

## 23. Critérios de aceitação

O SDS-600 — DASH será considerado tecnicamente suficiente quando:

1. o dashboard puder consumir o estado global oficial sem ambiguidades;
2. observação e controlo estiverem tecnicamente segregados;
3. o sistema só expuser ações compatíveis com estado e permissões;
4. alarmes e bloqueios puderem ser apresentados com prioridade e rastreabilidade;
5. histórico e logs forem consultáveis e exportáveis de forma controlada;
6. a interface assistida estiver limitada ao domínio autorizado;
7. falha do dashboard não comprometer a segurança operacional do sistema.

---

## 24. Dependências e próximos documentos

### 24.1 Dependências principais
- SDS-100 — CORE
- SDS-120 — CORE-INTERFACES
- SDS-200 — MARKET
- SDS-300 — DECISION
- SDS-400 — RISK
- SDS-500 — EXEC
- SDS-700 — RECOVERY
- SDS-800 — LEARN
- ODIN-TRACEABILITY-MATRIX

### 24.2 Próximos documentos recomendados
1. **SDS-700 — RECOVERY**
2. **SDS-800 — LEARN**

---

## 25. Conclusão

O SDS-600 fecha a camada técnica da superfície operacional humana do Odin.

Sem este documento, o dashboard correria o risco de se tornar:
- apenas uma UI bonita;
- uma fonte de estado contraditória;
- um atalho perigoso para contornar o CORE.

Com este documento, o DASH passa a ser:
- observável;
- controlado;
- auditável;
- compatível com a disciplina do resto do sistema.

Num sistema destes, um dashboard não pode ser apenas cómodo. Tem de ser seguro, legível e submisso à verdade do sistema.
