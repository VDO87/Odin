# ODIN-TEST-PLAN
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Plano transversal de testes  
**Objetivo:** Definir a estratégia de validação do Odin, as suites mínimas por fase, a evidência necessária para cada gate do roadmap e a ligação entre requisitos, casos de uso, SDS e execução de testes.

---

## 1. Finalidade do documento

O **ODIN-TEST-PLAN** existe para impedir que o Odin avance de fase com sensação subjetiva de segurança em vez de evidência técnica.

Os SDS já descrevem testes mínimos por módulo e a matriz de rastreabilidade já associa requisitos a escopos de teste.  
Este documento unifica essas intenções num plano operacional único, com:

- camadas de teste;
- suites mínimas por fase;
- cenários prioritários;
- fault-injection transversal;
- critérios de evidência para gates do roadmap.

---

## 2. Âmbito

### 2.1 Incluído
Este documento inclui:
- estratégia transversal de testes;
- taxonomia das suites;
- ambientes mínimos de teste;
- uso de simuladores e doubles;
- mapeamento para casos de uso;
- critérios de gate por fase;
- artefactos de evidência;
- regras de rastreabilidade.

### 2.2 Excluído
Este documento não inclui:
- implementação linha a linha dos testes;
- dados reais de broker em produção;
- performance tuning avançado;
- ensaios de carga distribuída;
- validação regulatória externa.

---

## 3. Objetivos do plano de testes

O plano de testes do Odin deverá garantir, no mínimo:

1. **Segurança operacional antes de funcionalidade visual**  
   O sistema deve provar que não opera fora das condições permitidas.

2. **Rastreabilidade entre requisito e evidência**  
   Nenhum requisito crítico deve ficar sem suite identificável.

3. **Validação progressiva por fase**  
   Cada gate do roadmap deve ter evidência própria.

4. **Deteção explícita de falhas de integridade**  
   Fault-injection e recovery não são opcionais.

5. **Separação entre teste de contrato e teste de cenário**  
   Contratos, módulos e fluxos ponta-a-ponta devem falhar de formas observáveis diferentes.

---

## 4. Princípios obrigatórios

- fail-safe testado, não apenas declarado;
- uma falha crítica deve ter caso de teste associado;
- bloqueios e kills devem ser testados como first-class behavior;
- restart/recovery deve ser tratado como cenário normal de engenharia;
- ambiente demo deve anteceder qualquer preparação real;
- evidência de teste deve ser preservada por fase.

---

## 5. Taxonomia das suites

### 5.1 Tipos mínimos de suite

| Tipo | Objetivo |
|---|---|
| `unit` | validar regras puras, guards, scoring, cálculos e transforms |
| `contract` | validar payloads, eventos, schemas e semântica mínima |
| `integration` | validar integração entre 2 ou mais módulos |
| `scenario` | validar fluxos ponta-a-ponta orientados a caso de uso |
| `fault_injection` | validar degradação, timeout, falha e recovery |
| `replay` | validar determinismo usando snapshots/eventos capturados |

### 5.2 Regra obrigatória
Requisitos `P1` devem aparecer pelo menos em `contract` ou `unit` e em `integration` ou `scenario`.

---

## 6. Ambientes mínimos de teste

### 6.1 Ambiente local de desenvolvimento
Usado para unit, contract e parte dos integration tests.

### 6.2 Ambiente de integração controlada
Usado para pipeline `MARKET -> DECISION -> RISK -> EXEC` em modo demo.

### 6.3 Ambiente de scenario/recovery
Usado para restart, falhas de persistência, divergência e recovery drills.

### 6.4 Doubles mínimos obrigatórios
- simulador de feed de mercado;
- simulador de risco/control plane;
- executor demo ou broker fake;
- relógio controlável para TTL e heartbeats;
- persistência local descartável;
- injetor de falhas de liveness e I/O.

---

## 7. Cobertura mínima por domínio

### 7.1 CORE
- state machine
- precedência de eventos
- guards de transição
- bloqueios ativos
- startup/shutdown
- heartbeat supervisor

### 7.2 MARKET
- validade do feed
- spread adaptativo
- janela macro/notícias
- prontidão e degradação
- `profile gate` e filtro de scope (`instrument_scope` / `feed_scope`)

### 7.3 RISK
- allow/restrict/block/kill
- persistência de kill
- bloqueio manual
- envelopes por modo

### 7.4 DECISION
- elegibilidade
- scoring
- seleção
- intenção operacional
- TTL e `max_slippage`

### 7.5 EXEC
- revalidação
- idempotência
- submissão demo
- expiração de intenção
- slippage
- divergência

### 7.6 RECOVERY
- reconstrução
- reconciliação
- confiança
- saída segura

### 7.7 DASH
- read-model oficial
- distinção observação/controlo
- visibilidade de bloqueios
- ações manuais autorizadas

### 7.8 LEARN
- snapshots
- aprovação
- shadow mode
- promoção
- rollback

---

## 8. Suites mínimas por fase do roadmap

### 8.1 F0 — Fundação de repositório

Suites mínimas:
- smoke check da estrutura de diretórios;
- validação de presença dos documentos obrigatórios;
- validação do ficheiro de configuração de exemplo;
- validação de convenções mínimas do repositório.

Gate de evidência:
- árvore do repositório conforme `ODIN-REPO-STRUCTURE`;
- docs-chave presentes;
- config example parseável;
- `.gitignore` e `CHANGELOG.md` presentes.

### 8.2 F1 — Núcleo operacional

Suites mínimas:
- unit tests da state machine;
- unit tests de guards do CORE;
- integration tests de startup com persistência;
- integration tests de kill persistente;
- fault-injection de heartbeat timeout;
- scenario de shutdown não limpo.

Gate de evidência:
- `REQ-CORE-001` a `REQ-CORE-006` cobertos;
- kill persistente demonstrado;
- recovery exigido após shutdown não limpo demonstrado;
- transições proibidas rejeitadas.

### 8.3 F2 — Consciência operacional

Suites mínimas:
- contract tests de payload MARKET e RISK;
- integration tests de `MARKET -> CORE`;
- integration tests de `RISK -> CORE`;
- scenario de mercado fechado/hostil;
- scenario de bloqueio por risco;
- fault-injection de feed degradado.

Gate de evidência:
- sistema não entra em `READY`/`ACTIVE` sem contexto válido;
- kill e bloqueio por risco entram no CORE corretamente;
- perda de integridade do feed produz reação conservadora.

### 8.4 F3 — Decisão e execução demo

Suites mínimas:
- unit tests de intenção operacional;
- contract tests de `execution_intent`;
- integration tests `DECISION -> EXEC`;
- scenario de intenção expirada;
- scenario de slippage acima do permitido;
- scenario de demo ponta-a-ponta.

Gate de evidência:
- pipeline demo completo funcional;
- intenção expirada nunca executada;
- divergência e slippage têm comportamento formalizado;
- racional técnico reconstruível.

### 8.5 F4 — Supervisão e recovery

Suites mínimas:
- integration tests `CORE -> DASH`;
- scenario de consulta operacional;
- scenario de reinício com recovery;
- fault-injection de divergência de execução;
- scenario de bloqueio manual e manutenção.

Gate de evidência:
- DASH reflete o estado oficial;
- recovery não retorna diretamente a `ACTIVE`;
- intervenção humana é exigida quando a confiança é insuficiente.

### 8.6 F5 — Endurecimento técnico

Suites mínimas:
- fault-injection de falhas de persistência;
- fault-injection de indisponibilidade de módulos críticos;
- replay determinístico de eventos;
- tests de regressão sobre bloqueios e precedência.

Gate de evidência:
- comportamento fail-safe mantido sob falha;
- regressões críticas detetadas antes de promoção;
- observabilidade suficiente para diagnóstico.

### 8.7 F6 — Operação real controlada

Suites mínimas:
- scenario de promoção de `DEMO` para `REAL` com gates reforçados;
- contract tests dos adaptadores reais;
- testes de permissões e configuração real;
- ensaios conservadores de rollback operacional.

Gate de evidência:
- `REAL` só é ativado sob configuração e liveness reforçados;
- rollback operacional documentado e treinado;
- suites críticas anteriores verdes.

### 8.8 F7 — Evolução controlada

Suites mínimas:
- scenario de criação de snapshot;
- scenario de shadow mode;
- scenario de promoção de versão;
- scenario de rollback;
- scenario de promoção bloqueada por governação;
- scenario de rollback bloqueado;
- validação de dispatch LEARN com payload válido/inválido;
- regressão funcional após promoção.

Gate de evidência:
- nenhuma alteração ativa sem snapshot;
- shadow mode com comparação auditável;
- rollback viável e rastreável;
- `blocking_reason_code` e `blocking_summary` validados nos bloqueios de governação.

### 8.9 Perfis de execução e instalação inicial

Suites mínimas:
- config sem profile explícito resolve para `lite`;
- `DASH-lite` não expõe queries nem ações LEARN;
- `MARKET` aplica em runtime o envelope do profile ativo em `CoreRuntimeController.ingest_market_sample(...)`, antes do `MarketSampleInput`;
- `lite` restringe `MARKET` a `1` instrumento, `1` feed, `news_guard` desligado e sem enriquecimento pesado;
- `standard/full` mantêm scope configurado e projetam restrições efetivas no `DASH` em `operation_focus.market_runtime`;
- execution ledger é persistido e consultável;
- base SQLite legada é migrada para a versão atual de schema;
- `INSTALL_ODIN.sh --dry-run --profile <...>` valida o corte sem efeitos colaterais.

Gate de evidência:
- `lite` desliga `LEARN`, shadow mode e memória auxiliar;
- `full` mantém superfície de evolução controlada disponível;
- `schema_meta`/`schema_migrations` ficam coerentes após `initialize()`;
- instalador rejeita combinações inválidas de profile/memória.

Evidência automatizada atual:
- `tests/integration/test_execution_profiles.py::test_config_defaults_to_lite_and_forces_memory_and_learn_off`
- `tests/integration/test_execution_profiles.py::test_dash_lite_projects_operation_focus_and_blocks_learn_actions`
- `tests/integration/test_execution_profiles.py::test_market_runtime_lite_enforces_minimal_envelope_and_projects_restrictions`
- `tests/integration/test_execution_profiles.py::test_market_runtime_standard_accepts_configured_second_instrument_and_feed`
- `tests/integration/test_execution_profiles.py::test_state_store_migrates_legacy_schema_and_keeps_execution_ledger_queryable`
- `tests/integration/test_execution_profiles.py::test_install_script_supports_dry_run_with_profiles`

---

## 9. Cenários obrigatórios por caso de uso

| Caso de uso | Tipo mínimo | Evidência principal |
|---|---|---|
| `UC-001` Arranque normal | integration + scenario | startup válido |
| `UC-002` Mercado fechado | integration | gating de mercado |
| `UC-003` Sem oportunidade | scenario | DECISION não emite intenção indevida |
| `UC-004` Operação Demo | scenario | pipeline demo ponta-a-ponta |
| `UC-005` Operação Real confirmada | scenario | EXEC confirmado dentro de regras |
| `UC-006` Bloqueio por risco | integration + scenario | `RISK -> CORE` bloqueia |
| `UC-007` Intenção invalidada | scenario | `EV-INTENTION-EXPIRED` |
| `UC-008` Divergência | fault_injection + scenario | EXEC/RECOVERY |
| `UC-009` Perda de feed | fault_injection | MARKET/CORE/RECOVERY |
| `UC-010` Reinício/recuperação | integration + recovery drill | reconstrução de estado |
| `UC-011` Pausa/retoma | scenario | CORE/DASH |
| `UC-012` Kill-switch | integration + recovery | kill persistente |
| `UC-013` Manutenção | scenario | perfil explícito de manutenção |
| `UC-014` Proposta de aprendizagem | scenario | proposta auditável |
| `UC-015` Ativação nova versão | scenario | snapshot + promoção |
| `UC-016` Rollback | scenario | reversão auditável |
| `UC-017` Consulta operacional | integration | read-model oficial |
| `UC-018` Exportação de logs | contract + scenario | exportação controlada |

---

## 10. Contract tests obrigatórios

### 10.1 Contratos mínimos a validar
- `core_event_envelope`
- `global_state_snapshot`
- `active_block_vector`
- `module_heartbeat`
- `execution_intent`
- payloads resumidos de MARKET, RISK, EXEC e RECOVERY
- `memory_advisory_context`

### 10.2 Regras obrigatórias
- versionamento de payload tem de ser validado;
- campos obrigatórios ausentes devem falhar explicitamente;
- contratos não suportados devem gerar erro rastreável;
- contract tests devem ser executáveis sem infraestrutura real.

---

## 11. Fault-injection transversal obrigatório

### 11.1 Injeções mínimas
- perda de heartbeat;
- latência excessiva;
- feed degradado;
- persistência inconsistente;
- falha de escrita crítica;
- evento com schema inválido;
- slippage acima do permitido;
- divergência pós-submissão;
- restart com shutdown não limpo.
- indisponibilidade da memória auxiliar durante consulta advisory.

### 11.2 Regra obrigatória
Cada fault test crítico deve declarar:
- falha injetada;
- trigger esperado;
- estado seguro esperado;
- evidência de observabilidade mínima.

---

## 12. Evidência exigida por gate

### 12.1 Artefactos mínimos
- relatório resumido das suites executadas;
- lista de requisitos cobertos;
- lista de casos de uso cobertos;
- logs relevantes ou referências de execução;
- anomalias abertas e respetiva severidade.

### 12.2 Regra obrigatória
Nenhum gate do roadmap deve ser dado por concluído apenas com “passou localmente”.  
É necessária evidência nomeada, preservável e revisável.

---

## 13. Estrutura recomendada de testes

```text
odin/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── scenarios/
│   ├── fault_injection/
│   ├── fixtures/
│   ├── simulators/
│   └── replay/
```

---

## 14. Ordem prática de implementação de testes

1. contract + unit do CORE
2. integration CORE + persistência
3. integration MARKET/RISK com CORE
4. contract + integration DECISION/EXEC
5. cenários demo ponta-a-ponta
6. recovery drills e fault-injection
7. read-model e controlo manual do DASH
8. governação do LEARN

---

## 15. Critérios de aceitação do plano

O **ODIN-TEST-PLAN** será considerado suficiente quando:

1. cada fase do roadmap tiver suites mínimas e evidência esperada;
2. requisitos `P1` estiverem ligados a tipos de teste executáveis;
3. `UC-001` a `UC-018` tiverem cobertura mínima declarada;
4. fault-injection e recovery fizerem parte do plano base;
5. existir distinção clara entre testes de contrato, integração e cenário;
6. o plano puder ser usado diretamente para criar backlog de testes.

---

## 16. Conclusão

O **ODIN-TEST-PLAN** transforma a intenção dispersa de teste do projeto Odin num programa de validação executável.

Sem este documento, o projeto pode parecer coerente mas avançar sem prova suficiente.  
Com ele, cada fase do roadmap passa a exigir evidência concreta de segurança, coerência e observabilidade.
