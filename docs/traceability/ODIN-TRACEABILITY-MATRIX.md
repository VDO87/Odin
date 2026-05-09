# ODIN-TRACEABILITY-MATRIX

**Versão:** 0.1  
**Estado:** Atualizado para fecho do corte principal F7 (2026-04-28)  
**Tipo de documento:** Matriz de rastreabilidade  
**Objetivo:** Ligar requisitos funcionais, módulos, casos de uso, modelo técnico, SDS, testes e estado de implementação do projeto Odin.

> Nota de contexto: esta matriz foca rastreabilidade de requisitos.
> Para estado operacional atual da consola/runtime e comandos de retoma, consultar
> `docs/runbooks/ODIN-SESSION-HANDOFF.md`.

---

## 1. Finalidade do documento

A Matriz de Rastreabilidade do Odin existe para garantir que o projeto mantém controlo sobre a cadeia completa:

**requisito -> módulo -> caso de uso -> modelo técnico -> SDS -> teste -> implementação**

Sem esta matriz, o risco é elevado:
- requisitos bons mas perdidos na implementação;
- módulos implementados sem cobertura de casos de uso;
- testes sem alinhamento com requisitos reais;
- SDS a divergir do FSD;
- alterações sem impacto documental claro.

---

## 2. Âmbito

### 2.1 Incluído
Este documento inclui:
- requisitos funcionais macro e intermédios;
- ligação ao documento FSD de origem;
- módulo responsável;
- casos de uso associados;
- documento técnico/modelo associado;
- SDS alvo;
- teste previsto;
- prioridade;
- estado de implementação.

### 2.2 Excluído
Este documento não inclui:
- detalhe do código fonte;
- casos de teste completos;
- resultados de execução de testes;
- gestão detalhada de backlog de desenvolvimento.

---

## 3. Convenções

### 3.1 Estrutura do ID de requisito
Formato recomendado:

`REQ-<MÓDULO>-<NÚMERO>`

Exemplos:
- `REQ-CORE-001`
- `REQ-MARKET-004`
- `REQ-RISK-003`

### 3.2 Estados de implementação
- `NOT_STARTED`
- `PLANNED`
- `IN_PROGRESS`
- `IMPLEMENTED`
- `TESTED`
- `VALIDATED`
- `BLOCKED`
- `DEFERRED`

### 3.3 Prioridade
- `P1` — crítico
- `P2` — importante
- `P3` — útil / complementar

---

## 4. Estrutura da matriz

Cada linha da matriz deverá conter, no mínimo:

| Campo | Descrição |
|---|---|
| `requirement_id` | ID único do requisito |
| `module` | Módulo principal |
| `source_document` | Documento FSD ou matriz de origem |
| `requirement_summary` | Resumo do requisito |
| `use_cases` | Casos de uso associados |
| `technical_model` | Documento técnico intermédio associado |
| `target_sds` | SDS onde será implementado tecnicamente |
| `test_scope` | Tipo de teste esperado |
| `priority` | Prioridade |
| `implementation_status` | Estado atual |
| `notes` | Observações complementares |

---

## 5. Matriz principal de rastreabilidade

| requirement_id | module | source_document | requirement_summary | use_cases | technical_model | target_sds | test_scope | priority | implementation_status | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-CORE-001 | CORE | FSD-100 | O sistema deve manter um estado global único e coerente | UC-001, UC-010, UC-011 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-100 CORE | unit + integration | P1 | TESTED | base da state machine coberta em unit/integration |
| REQ-CORE-002 | CORE | FSD-100 | O sistema deve rejeitar transições inválidas | UC-001, UC-011 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-100 CORE | unit + state transition | P1 | TESTED | guard com precedência explícita (`kill>manual>fault>recovery>risk`) validado em `test_active_transition_uses_kill_precedence_over_manual_and_recovery` e `test_maintenance_exit_is_rejected_while_manual_block_is_active` |
| REQ-CORE-003 | CORE | FSD-100 / v0.4 | O CORE deve supervisionar heartbeat de módulos críticos | UC-010, UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-100 CORE | integration + fault injection | P1 | TESTED | MARKET/RISK/EXEC mínimos cobertos em integration/fault |
| REQ-CORE-004 | CORE | FSD-100 / v0.4 | O arranque deve validar kill persistente antes de qualquer progressão operacional | UC-001, UC-010, UC-012 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-100 CORE / SDS-110 CORE-PERSISTENCE | integration + recovery | P1 | TESTED | requisito crítico com cobertura de startup/persistence |
| REQ-CORE-005 | CORE | FSD-100 / v0.4 | O CORE deve manter vetor completo de bloqueios ativos | UC-006, UC-008, UC-010, UC-012 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-100 CORE | unit + integration | P1 | TESTED | coexistência e precedência do vetor validadas (`test_manual_block_has_precedence_over_fault_in_dominant_reason` + `test_core_health_metrics_expose_full_block_vector_with_precedence`) |
| REQ-CORE-006 | CORE | FSD-100 | Recovery não pode regressar diretamente a operação ativa | UC-010 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-100 CORE / SDS-700 RECOVERY | integration | P1 | TESTED | retoma validada para `IDLE`/`MONITORING` sem salto para `ACTIVE` em `test_unexpected_restart_enters_recovery_and_exits_safely_to_idle` e `test_heartbeat_timeout_recovery_returns_to_monitoring_restricted` |
| REQ-CORE-007 | CORE | FSD-100 / SDS-110 | A persistência deve versionar schema, migrar legado e manter execution ledger consultável | UC-010, UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-110 CORE-PERSISTENCE | integration | P1 | TESTED | `test_state_store_migrates_legacy_schema_and_keeps_execution_ledger_queryable` |

| REQ-MARKET-001 | MARKET | FSD-200 | O sistema deve distinguir mercado válido, degradado, inválido e indisponível | UC-002, UC-003, UC-009 | — | SDS-200 MARKET | unit + integration | P1 | PLANNED | base do state model do market |
| REQ-MARKET-002 | MARKET | FSD-200 / v0.3 | O contexto deve ser forçado para sensível/hostil em janela macro crítica | UC-002, UC-003, UC-005 | — | SDS-200 MARKET | integration | P1 | PLANNED | filtro preventivo de notícias |
| REQ-MARKET-003 | MARKET | FSD-200 / v0.4 | Spread anormal deve degradar o market mesmo com feed vivo | UC-002, UC-005, UC-009 | — | SDS-200 MARKET | unit + market-sim | P1 | PLANNED | spread adaptativo |
| REQ-MARKET-004 | MARKET | FSD-200 | O módulo deve publicar prontidão funcional clara ao CORE | UC-001, UC-003, UC-005 | — | SDS-200 MARKET | integration | P1 | TESTED | pronto/não-pronto validado por pipeline integrado |
| REQ-MARKET-005 | MARKET | FSD-200 / F7 | O `MarketProfileGate` deve aplicar enforcement real de scope/restrições antes da avaliação principal | UC-002, UC-009, UC-017 | — | SDS-200 MARKET | integration | P1 | TESTED | `ingest_market_sample` + projeção em `operation_focus.market_runtime` |

| REQ-DECISION-001 | DECISION | FSD-300 | O sistema deve avaliar táticas e produzir decisão auditável | UC-003, UC-004, UC-005, UC-006 | — | SDS-300 DECISION | unit + scenario | P1 | PLANNED | scoring/racional |
| REQ-DECISION-002 | DECISION | FSD-300 / v0.2 | A intenção operacional deve incluir `intent_id`, `decision_cycle_id`, TTL e expiração | UC-004, UC-005, UC-007 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-300 DECISION / SDS-500 EXEC | unit + integration | P1 | PLANNED | requisito de concorrência temporal |
| REQ-DECISION-003 | DECISION | FSD-300 / v0.4 | A intenção operacional deve incluir `max_slippage` | UC-005, UC-007 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-300 DECISION / SDS-500 EXEC | integration | P1 | PLANNED | execução tolerada por desvio |

| REQ-RISK-001 | RISK | FSD-400 | O sistema deve bloquear por risco ao ultrapassar limites críticos | UC-006, UC-012 | — | SDS-400 RISK | unit + integration | P1 | TESTED | bloqueio por limite diário e retoma após clear cobertos em `test_risk_block_requires_clear_before_resume` |
| REQ-RISK-002 | RISK | FSD-400 / v0.4 | Kill-switch deve persistir fora de memória volátil | UC-012, UC-010 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-400 RISK / SDS-110 CORE-PERSISTENCE | integration + recovery | P1 | TESTED | kill persistente validado em `test_kill_active_from_risk_enters_blocked_fault_and_persists` com `reason_code` estável |
| REQ-RISK-003 | RISK | FSD-400 / v0.3 | Bloqueio manual não pode ser limpo automaticamente | UC-011, UC-012 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-400 RISK / SDS-100 CORE | integration | P1 | TESTED | limpeza manual explícita exigida e bloqueio de saída de recovery cobertos em `test_manual_block_requires_explicit_clear_and_blocks_recovery_exit` |
| REQ-RISK-004 | RISK | FSD-400 | O RISK deve distinguir allow/restrict/block/kill | UC-003, UC-005, UC-006, UC-012 | — | SDS-400 RISK | unit | P1 | TESTED | matriz de decisão `ALLOW/RESTRICT/BLOCK/KILL` coberta em `tests/unit/test_risk_module.py` |

| REQ-EXEC-001 | EXEC | FSD-500 | O EXEC deve revalidar permissões antes da submissão | UC-004, UC-005, UC-007 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-500 EXEC | integration | P1 | TESTED | precheck de modo/estado/kill/risco/mercado/canal coberto por cenários demo e real |
| REQ-EXEC-002 | EXEC | FSD-500 / v0.3 | O EXEC deve emitir `EV-INTENTION-EXPIRED` quando a intenção expirar | UC-007 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-500 EXEC | unit + integration | P1 | TESTED | emissão e persistência auditável validadas em `test_expired_intent_never_executes` e `test_expired_intent_persists_reason_code_in_execution_ledger` |
| REQ-EXEC-003 | EXEC | FSD-500 / v0.4 | O EXEC deve rejeitar/assinalar execução fora de `max_slippage` | UC-005, UC-007, UC-008 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-500 EXEC | integration + broker-sim | P1 | TESTED | rejeição pré-submissão e divergência pós-submissão cobertas com reason codes estáveis |
| REQ-EXEC-004 | EXEC | FSD-500 | O EXEC deve detetar divergência crítica | UC-008, UC-010 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-500 EXEC / SDS-700 RECOVERY | integration + fault injection | P1 | TESTED | `EV-EXEC-DIVERGENCE` e bloqueio em `CORE` validados em demo flow |
| REQ-EXEC-005 | EXEC | FSD-500 | O EXEC deve evitar duplicação cega | UC-005, UC-007, UC-008 | — | SDS-500 EXEC | unit + integration | P1 | TESTED | deduplicação + evidência persistida (`was_deduplicated`) em `test_exec_divergence_reason_and_idempotency_are_persisted` |

| REQ-RECOVERY-001 | RECOVERY | FSD-700 | O sistema deve reconstruir estado após reinício inesperado | UC-010 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-700 RECOVERY | integration + recovery drill | P1 | PLANNED | arranque seguro |
| REQ-RECOVERY-002 | RECOVERY | FSD-700 | Recovery deve distinguir validado, restrito, inconclusivo e falhado | UC-008, UC-009, UC-010 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-700 RECOVERY | integration | P1 | PLANNED | saída formal do incidente |
| REQ-RECOVERY-003 | RECOVERY | FSD-700 / v0.4 | Recovery não pode limpar kill persistente nem bloqueio manual | UC-010, UC-012 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-700 RECOVERY / SDS-100 CORE | integration | P1 | TESTED | precedência transversal confirmada (`test_recovery_is_blocked_by_kill_precedence_when_kill_is_persisted`, `test_recovery_is_blocked_by_manual_precedence_when_manual_block_is_persisted`, `test_manual_block_requires_explicit_clear_and_blocks_recovery_exit`) |

| REQ-DASH-001 | DASH | FSD-600 | O dashboard deve refletir o estado oficial do CORE | UC-017 | — | SDS-600 DASH | UI integration | P1 | TESTED | projeção oficial via `CoreDashBridge.project_state` |
| REQ-DASH-002 | DASH | FSD-600 / v0.3 | O dashboard deve distinguir observação de controlo | UC-011, UC-013, UC-017 | — | SDS-600 DASH | UI + permission tests | P1 | TESTED | gates de ações e rejeições explícitas no dispatch validados no corte F7 |
| REQ-DASH-003 | DASH | FSD-600 / v0.4 | O dashboard deve mostrar vetor completo de bloqueios ativos | UC-006, UC-008, UC-010, UC-012, UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-600 DASH | UI integration | P1 | PLANNED | causa raiz visível |
| REQ-DASH-004 | DASH | FSD-600 / v0.4 | A entrada em manutenção deve pedir perfil explícito | UC-013 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-600 DASH / SDS-100 CORE | UI + integration | P2 | TESTED | rejeição explícita `maintenance_profile_required` sem fallback implícito |
| REQ-DASH-005 | DASH | FSD-600 / F7 | O `DASH-lite` deve projetar `operation_focus.market_runtime` e `last_execution` para foco operacional | UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-600 DASH / SDS-110 CORE-PERSISTENCE | integration | P1 | TESTED | `test_dash_lite_projects_operation_focus_and_blocks_learn_actions` |
| REQ-OPS-001 | OPERATOR_CONSOLE | Post-F7 OPERATOR CONSOLE | Todos os comandos operacionais da consola devem passar pelo `CommandGateway` | UC-011, UC-013, UC-017, UC-018 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-600 DASH / SDS-120 CORE-INTERFACES | integration | P1 | TESTED | comandos v1 encapsulados em `operator_console.gateway.CommandGateway` |
| REQ-OPS-002 | OPERATOR_CONSOLE | Post-F7 OPERATOR CONSOLE | Comandos críticos (`stop`, `pause`, `resume`) devem exigir confirmação explícita | UC-011, UC-013 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-600 DASH / SDS-100 CORE | integration | P1 | TESTED | gate `confirmation_required` validado em `test_command_gateway_critical_controls_require_confirmation` |
| REQ-OPS-003 | OPERATOR_CONSOLE | Post-F7 OPERATOR CONSOLE | Configuração deve ser consultada/validada por preview staged antes de aplicação | UC-017, UC-018 | — | SDS-120 CORE-INTERFACES / SDS-600 DASH | integration | P2 | TESTED | `get-config` + `validate-config` com staged patch em `test_command_gateway_status_export_and_config_validation` |
| REQ-OPS-004 | OPERATOR_CONSOLE | Post-F7 OPERATOR CONSOLE | Dashboard web local deve expor estado global, health, liveness e logs sem mutação direta de CORE | UC-017, UC-018 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-600 DASH | integration | P2 | TESTED | superfície HTTP mínima validada em `test_operator_console_http_surface_exposes_status_and_safe_command_gate` |
| REQ-OPS-005 | OPERATOR_CONSOLE | Post-F7 OPERATOR CONSOLE | Contratos de chat/Telegram/OpenAI e adapters MT5/XTB devem ser advisory/bridge e não executar ordens diretamente; Telegram só via `CommandGateway` + confirmação | UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-500 EXEC / SDS-600 DASH / SDS-900 INTELLIGENCE-LAYER | contract | P1 | TESTED | contratos em `shared/contracts_parts/operator_console.py` e validações em `test_bridge_contracts_enforce_safety_assumptions` |
| REQ-OPS-006 | OPERATOR_CONSOLE | Post-F7 OPERATOR CONSOLE | Modelos de routing (`ExecutionVenue`, `AssetClass`, `PortfolioBucket`, `OrderWorkflow`) devem impor política inicial: MT5 foco FOREX/AUTO_DEMO; XTB assistido para ETF/STOCK/FIRE; sem AUTO_REAL ativo em XTB | UC-017, UC-018 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-500 EXEC / SDS-600 DASH | contract + unit | P1 | TESTED | enums em `shared/enums.py`; guards contratuais em `ExecAdapterBridgeRequest`; cobertura em `test_execution_routing_enums_are_declared` e `test_bridge_contracts_enforce_safety_assumptions` |
| REQ-EXT-001 | EXTERNAL_DATA | External Market Data Providers v1 | Dados externos devem entrar apenas via `ExternalDataService` com fallback obrigatório para `DemoProvider` e sem dependência crítica de internet | UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-200 MARKET / SDS-600 DASH | integration + unit | P1 | TESTED | `external_data/service.py`; cobertura em `test_external_data_service_lite_profile_uses_demo_without_real_dependencies` e `test_external_data_payloads_are_available_in_console_service` |
| REQ-EXT-002 | EXTERNAL_DATA | External Market Data Providers v1 | Falha/rate-limit/configuração ausente de APIs externas não pode matar `CORE`; serviço deve aplicar cache TTL e rate limiting | UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-200 MARKET / SDS-600 DASH | integration + unit | P1 | TESTED | `ExternalDataService` com `TTLCache` e `FixedWindowRateLimiter`; cobertura em `test_external_data_service_falls_back_to_demo_when_real_provider_fails` |
| REQ-EXT-003 | EXTERNAL_DATA | External Market Data Providers v1 | Dados externos não podem executar ordens nem ser autoridade de `CORE/RISK/EXEC` | UC-017, UC-018 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-500 EXEC / SDS-600 DASH | contract + integration | P1 | TESTED | payloads `core_authority=false` e `data_can_execute_orders=false` em `/api/external/status` |

| REQ-LEARN-001 | LEARN | FSD-800 | O sistema deve criar snapshot antes de alterar versão ativa | UC-015, UC-016 | — | SDS-800 LEARN | integration | P1 | TESTED | snapshots pré-ativação e fluxo de ativação/rollback cobertos em integration |
| REQ-LEARN-002 | LEARN | FSD-800 / v0.3 | O sistema deve suportar shadow mode/canary controlado | UC-014, UC-015, UC-016 | — | SDS-800 LEARN | simulation + integration | P2 | TESTED | sessões shadow, recomendação e governação negativa validadas no corte F7 |
| REQ-LEARN-003 | LEARN | FSD-800 | Rollback deve ser auditável e reversível | UC-016 | — | SDS-800 LEARN | integration | P1 | TESTED | trilho auditável persistido e rollback operacional validado end-to-end |

| REQ-INT-001 | INTELLIGENCE | SDS-900 / Post-F7 | A Intelligence Layer deve ser advisory e não autoritativa | UC-017, UC-014, UC-015 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-900 INTELLIGENCE-LAYER | unit + integration | P1 | PLANNED | sem mutação direta de estado crítico |
| REQ-INT-002 | INTELLIGENCE | SDS-900 / Post-F7 | A camada não pode alterar diretamente CORE/RISK/EXEC/RECOVERY | UC-010, UC-012, UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-900 INTELLIGENCE-LAYER | boundary + integration | P1 | PLANNED | bloqueio explícito de operações proibidas |
| REQ-INT-003 | INTELLIGENCE | SDS-900 / Post-F7 | A camada não pode limpar bloqueios nem acionar execução | UC-012, UC-017 | ODIN-CORE-STATE-AND-EVENT-MODEL | SDS-900 INTELLIGENCE-LAYER | boundary + security | P1 | PLANNED | sem clear de block vector/kill e sem submit de ordens |
| REQ-INT-004 | INTELLIGENCE | SDS-900 / Post-F7 | Influência em DECISION/LEARN deve ficar congelada em advisory_snapshot | UC-014, UC-015, UC-017 | ODIN-AUXILIARY-MEMORY-MODEL | SDS-900 INTELLIGENCE-LAYER | contract + integration | P1 | PLANNED | sem snapshot advisory não há influência persistente |
| REQ-INT-005 | INTELLIGENCE | SDS-900 / Post-F7 | A camada deve respeitar gating por profile (`lite`, `standard`, `full`) | UC-017 | ODIN-AUXILIARY-MEMORY-MODEL | SDS-900 INTELLIGENCE-LAYER | unit + integration | P1 | PLANNED | `lite` desligado/manual, `standard` cenário leve, `full` advisory completo |
| REQ-INT-006 | INTELLIGENCE | SDS-900 / Post-F7 | Contratos `advisory_request/response/snapshot`, `scenario_context` e `memory_context_ref` devem ser estáveis e auditáveis | UC-017, UC-014 | ODIN-AUXILIARY-MEMORY-MODEL | SDS-900 INTELLIGENCE-LAYER | contract | P2 | PLANNED | serialização e rastreabilidade por digest/ref |

---

## 6. Matriz resumida por documento de origem

| source_document | quantidade_aproximada_de_requisitos_mapeados | observações |
|---|---|---|
| FSD-100 CORE | 7 | estado global, transições, heartbeat, bloqueios, persistência versionada |
| FSD-200 MARKET | 5 | validade, contexto, spread, prontidão, enforcement por profile |
| FSD-300 DECISION | 3 | decisão, intenção, slippage |
| FSD-400 RISK | 4 | bloqueio, kill persistente, precedência |
| FSD-500 EXEC | 5 | revalidação, expiração, slippage, divergência, idempotência |
| FSD-600 DASH | 5 | estado oficial, observação/controlo, bloqueios, manutenção, foco operacional em `DASH-lite` |
| FSD-700 RECOVERY | 3 | reconstrução, classificação de recovery, precedência |
| FSD-800 LEARN | 3 | snapshot, shadow mode, rollback |
| Post-F7 OPERATOR CONSOLE | 6 | command gateway, confirmação crítica, staged config, dashboard local, contracts bridge/advisory, routing MT5/XTB por workflow/bucket |
| External Market Data Providers v1 | 3 | fallback demo obrigatório, cache/rate-limit, boundaries de autoridade/execução |
| SDS-900 INTELLIGENCE-LAYER | 6 | advisory de cenário/reasoning/memória com boundaries e gating por profile |

---

## 7. Mapeamento de casos de uso para teste

| caso_de_uso | foco principal de teste | módulos principais |
|---|---|---|
| UC-001 | arranque limpo | CORE, MARKET, DASH |
| UC-002 | mercado fechado | MARKET, CORE, DASH |
| UC-003 | sem oportunidade válida | DECISION, MARKET, RISK |
| UC-004 | execução demo | DECISION, EXEC, DASH |
| UC-005 | execução real confirmada | DECISION, RISK, EXEC, CORE |
| UC-006 | bloqueio por risco | RISK, DECISION, DASH |
| UC-007 | intenção invalidada antes da execução | EXEC, CORE, MARKET, RISK |
| UC-008 | divergência de execução | EXEC, RECOVERY, CORE, DASH |
| UC-009 | perda de feed | MARKET, CORE, RECOVERY |
| UC-010 | reinício com recovery | CORE, RECOVERY, EXEC, RISK |
| UC-011 | pausa e retoma | DASH, CORE |
| UC-012 | kill-switch | RISK, CORE, DASH |
| UC-013 | manutenção | DASH, CORE, EXEC |
| UC-014 | proposta de aprendizagem | LEARN, DASH |
| UC-015 | ativação de nova versão | LEARN, CORE, DASH |
| UC-016 | rollback | LEARN, CORE, DASH |
| UC-017 | consulta operacional | DASH, CORE, todos os módulos |
| UC-018 | exportação de logs | DASH, logging transversal |

---

## 8. Próximo uso desta matriz

Esta matriz deverá ser usada para:

1. derivar backlog técnico do SDS;
2. criar a matriz de testes;
3. marcar estado real de implementação;
4. identificar requisitos órfãos;
5. validar se cada módulo tem:
   - requisito;
   - caso de uso;
   - documento técnico;
   - teste previsto.

### 8.1 Atualização de referência F7

No fecho do corte principal F7 (2026-04-28), os requisitos `REQ-LEARN-001..003` e os reforços de governação em `REQ-DASH-002` passaram para estado `TESTED`, em linha com:
- `docs/plans/ODIN-F7-HANDOFF.md`
- `tests/integration/test_learn_dash_core_flow.py`
- `tests/unit/test_learn_module.py`

### 8.2 Atualização de referência OPERATOR CONSOLE

No corte inicial do OPERATOR CONSOLE (2026-04-28), os requisitos `REQ-OPS-001..005` passaram para `TESTED` com cobertura em:
- `tests/integration/test_operator_console_flow.py`
- `tests/contract/test_operator_console_contracts.py`

---

## 9. Regras de governação

- Nenhum requisito crítico P1 deve avançar para implementação sem `target_sds` definido.
- Nenhum requisito crítico P1 deve ser marcado como `IMPLEMENTED` sem `test_scope` definido.
- Alterações ao FSD devem refletir-se nesta matriz.
- Novos eventos, estados ou bloqueios do CORE devem ser revistos contra:
  - ODIN-CORE-STATE-AND-EVENT-MODEL
  - SDS-100 CORE
  - esta matriz de rastreabilidade

---

## 10. Próximos documentos recomendados

Após esta matriz, a ordem técnica recomendada é:

1. **SDS-110 — CORE-PERSISTENCE**
2. **SDS-120 — CORE-INTERFACES**
3. **SDS-200 — MARKET**
4. **SDS-400 — RISK**
5. **SDS-500 — EXEC**

---

## 11. Conclusão

A ODIN-TRACEABILITY-MATRIX passa a ser o documento que liga a arquitetura funcional à execução real do projeto.

É ela que permite responder, sem improviso:
- que requisito estamos a implementar;
- em que documento esse requisito nasceu;
- que caso de uso valida o seu comportamento;
- que SDS o descreve tecnicamente;
- que teste o comprova;
- e em que estado real se encontra.

Sem esta matriz, o projeto corre o risco de crescer por blocos isolados.  
Com esta matriz, o Odin passa a ter controlo de engenharia sobre a sua própria evolução.
