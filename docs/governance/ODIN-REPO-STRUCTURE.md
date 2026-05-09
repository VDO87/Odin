# ODIN-REPO-STRUCTURE
## Projeto Odin

**Versão:** 0.2  
**Estado:** Baseline estrutural aplicada  
**Tipo de documento:** Estrutura de repositório  
**Objetivo:** Definir a estrutura física e lógica do repositório do Odin, alinhada com os FSD, SDS, matriz de rastreabilidade e estratégia de implementação faseada.

---

## 1. Finalidade do documento

Este documento define **como o repositório do Odin deve ser organizado** para suportar:

- separação de responsabilidades por módulo;
- evolução faseada sem caos estrutural;
- rastreabilidade entre documentação, código e testes;
- runtime previsível;
- logging e persistência em local conhecido;
- configuração controlada;
- baixo acoplamento entre componentes.

O objetivo não é “ter uma árvore bonita”.  
O objetivo é impedir:
- mistura de domínios;
- ficheiros órfãos;
- duplicação de modelos;
- código de infraestrutura espalhado;
- runtime e documentação misturados;
- dívida técnica estrutural logo desde o início.

---

## 2. Princípios de organização do repositório

### 2.1 Domínio antes de conveniência
Os diretórios devem seguir os domínios funcionais/técnicos do Odin, não apenas preferências momentâneas de desenvolvimento.

### 2.2 Código e runtime são coisas diferentes
Código fonte, configuração, dados de runtime, logs e backups não devem partilhar o mesmo espaço lógico.

### 2.3 Documentação não deve ficar perdida
Os artefactos FSD/SDS/matrizes devem estar organizados de forma estável e navegável.

### 2.4 Testes ao lado da arquitetura, não no fim
A estrutura do repositório deve prever testes desde o início.

### 2.5 Shared não é lixo transversal
Só deve ir para `shared/` o que é realmente reutilizável e transversal.  
Não deve servir para esconder acoplamento mal resolvido.

---

## 3. Estrutura de topo recomendada

```text
odin/
├── docs/
├── src/
├── tests/
├── runtime/
├── config/
├── scripts/
├── tools/
├── assets/
├── .github/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── LICENSE (se aplicável)
```

### 3.1 Significado de cada diretório
- `docs/` → documentação funcional, técnica e operacional
- `src/` → código fonte da aplicação
- `tests/` → testes unitários, integração, fault-injection e cenários
- `runtime/` → estado transitório local, logs, snapshots e artefactos operacionais
  - incluindo memória auxiliar local quando configurada
- `config/` → ficheiros de configuração versionados e templates
- `scripts/` → scripts operacionais de build, bootstrap, migração e manutenção
- `tools/` → utilitários auxiliares e tooling interno
- `assets/` → imagens, templates visuais, ficheiros estáticos
- `.github/` → workflows e automação do repositório

---

## 4. Estrutura documental recomendada

```text
docs/
├── fsd/
├── sds/
├── models/
├── traceability/
├── plans/
├── runbooks/
└── governance/
```

### 4.1 Subdiretórios documentais

#### `docs/fsd/`
Documentos funcionais consolidados.
Exemplos:
- `ODIN_FSD_Consolidado_v0_5.md`

#### `docs/sds/`
Documentos técnicos por módulo.
Exemplos:
- `SDS-100-CORE.md`
- `SDS-110-CORE-PERSISTENCE.md`
- `SDS-120-CORE-INTERFACES.md`
- `SDS-200-MARKET.md`
- `SDS-300-DECISION.md`
- `SDS-400-RISK.md`
- `SDS-500-EXEC.md`
- `SDS-600-DASH.md`
- `SDS-700-RECOVERY.md`
- `SDS-800-LEARN.md`
- `ODIN-SDS-MASTER.md`

#### `docs/models/`
Modelos técnicos canónicos.
Exemplos:
- `ODIN-CORE-STATE-AND-EVENT-MODEL.md`
- `ODIN-AUXILIARY-MEMORY-MODEL.md`

#### `docs/traceability/`
Matriz de rastreabilidade e derivados.
Exemplos:
- `ODIN-TRACEABILITY-MATRIX.md`

#### `docs/plans/`
Planos operacionais/técnicos.
Exemplos:
- `ODIN-TEST-PLAN.md`
- `ODIN-IMPLEMENTATION-ROADMAP.md`

#### `docs/runbooks/`
Procedimentos operacionais.
Exemplos:
- `ODIN-RUNBOOK-v0.1.md`
- `ODIN-UBUNTU-SERVER-INSTALL.md`

#### `docs/governance/`
Regras de governação, decisões estruturais e convenções.
- `ODIN-REPO-STRUCTURE.md`
- `ODIN-ENGINEERING-RULES.md`
- `ODIN-REQUIRED-SOFTWARE.md`

---

## 5. Estrutura de código recomendada

```text
src/
├── apps/
├── core/
├── market/
├── decision/
├── risk/
├── exec/
├── dash/
├── recovery/
├── learn/
├── shared/
├── persistence/
├── messaging/
├── observability/
└── security/
```

---

## 6. Significado dos domínios de código

### 6.1 `apps/`
Entrypoints da aplicação.

Exemplos:
- `apps/core_service/`
- `apps/dash_app/`
- `apps/simulation_runner/`

### 6.2 `core/`
Núcleo do sistema.
Deve conter:
- state machine
- transições
- guards
- block manager
- heartbeat supervisor
- state publisher

### 6.3 `market/`
Ingestão, validação e contexto de mercado.

### 6.4 `decision/`
Motor de decisão, scoring, elegibilidade, intenção operacional.

### 6.5 `risk/`
Risco, limites, bloqueios, kill-switch, envelopes por modo.

### 6.6 `exec/`
Execução, validação pré-submissão, reconciliação, slippage, divergências.

### 6.7 `dash/`
Camada de supervisão, view models, controlo manual, alarmes, logs e interface assistida.

### 6.8 `recovery/`
Reconstrução de estado, reconciliação e retoma segura.

### 6.9 `learn/`
Aprendizagem, snapshots, propostas, shadow mode, promoção e rollback.

### 6.10 `shared/`
Tipos, enums, modelos canónicos, utilitários transversais e contratos comuns.

### 6.11 `persistence/`
Abstrações e backends de persistência.

### 6.12 `messaging/`
Envelope de eventos, roteamento, filas, serialização e contratos internos.

### 6.13 `observability/`
Logging, métricas, tracing e projeções de saúde técnica.

### 6.14 `security/`
Controlo de permissões, autenticação local, auditoria de ações humanas e regras de acesso.

---

## 7. Estrutura interna recomendada por módulo

Modelo recomendado para cada módulo principal:

```text
<module>/
├── orchestrator/
├── models/
├── services/
├── policies/
├── publishers/
├── handlers/
├── validators/
├── adapters/
└── audit/
```

### 7.1 Significado
- `orchestrator/` → coordenação principal do módulo
- `models/` → modelos internos e DTOs do módulo
- `services/` → lógica de domínio principal
- `policies/` → políticas, regras e estratégias configuráveis
- `publishers/` → publicação de estados/eventos
- `handlers/` → tratamento de mensagens/comandos
- `validators/` → validações estruturais e guards
- `adapters/` → integração com persistência, APIs, sistemas externos
- `audit/` → logging específico do módulo

---

## 8. Estrutura detalhada recomendada para módulos críticos

### 8.1 `src/core/`

```text
src/core/
├── orchestrator/
├── state_machine/
├── transitions/
├── guards/
├── blocks/
├── heartbeat/
├── readiness/
├── recovery_bridge/
├── publishers/
├── handlers/
├── models/
└── audit/
```

### 8.2 `src/decision/`

```text
src/decision/
├── engine/
├── cycle_runner/
├── input_snapshot/
├── tactics/
├── eligibility/
├── scoring/
├── confluence/
├── selector/
├── intent/
├── rationale/
├── publishers/
└── audit/
```

### 8.3 `src/exec/`

```text
src/exec/
├── orchestrator/
├── pre_validation/
├── submission/
├── confirmation/
├── reconciliation/
├── slippage/
├── divergence/
├── publishers/
└── audit/
```

### 8.4 `src/recovery/`

```text
src/recovery/
├── orchestrator/
├── incident_classifier/
├── context_loader/
├── observed_state/
├── reconstruction/
├── reconciliation/
├── confidence/
├── exit_guard/
├── intervention/
├── publishers/
└── audit/
```

### 8.5 `src/learn/`

```text
src/learn/
├── orchestrator/
├── history/
├── dataset/
├── analysis/
├── proposals/
├── boundaries/
├── snapshots/
├── approval/
├── shadow/
├── promotion/
├── activation/
├── rollback/
├── publishers/
└── audit/
```

---

## 9. Estrutura de modelos partilhados

```text
src/shared/
├── enums/
├── contracts/
├── models/
├── types/
├── time/
├── ids/
├── utils/
└── errors/
```

### 9.1 Conteúdo esperado
- enums canónicos de estados, modos, severidades e eventos
- contratos-base de mensagens
- tipos comuns do sistema
- geradores/validadores de IDs
- utilitários de tempo UTC
- tipos de erro normalizados

### 9.2 Regra obrigatória
Se um tipo só pertence a um módulo, não deve ir para `shared/`.

---

## 10. Estrutura de persistência

```text
src/persistence/
├── interfaces/
├── sqlite/
├── file_store/
├── migrations/
├── serializers/
└── validators/
```

### 10.1 Objetivo
Encapsular:
- `PersistentStateStore`
- snapshots
- kill flag
- vetor de bloqueios
- runtime markers
- recovery snapshots

### 10.2 Regra obrigatória
O código de domínio não deve conhecer diretamente o backend concreto quando isso puder ser abstraído.

---

## 11. Estrutura de messaging

```text
src/messaging/
├── envelopes/
├── event_bus/
├── routers/
├── queues/
├── serializers/
├── subscribers/
└── publishers/
```

### 11.1 Objetivo
Centralizar:
- envelopes de eventos
- filas internas
- roteamento
- serialização
- publishers/subscribers

### 11.2 Regra obrigatória
A semântica dos eventos deve viver aqui ou em `shared/contracts`, nunca dispersa por handlers avulsos.

---

## 12. Estrutura de observability

```text
src/observability/
├── logging/
├── metrics/
├── health/
├── alerts/
└── tracing/
```

### 12.1 Objetivo
Unificar:
- logging estruturado
- métricas técnicas
- health checks
- alertas internos
- tracing/correlation ids

---

## 13. Estrutura de segurança

```text
src/security/
├── auth/
├── permissions/
├── audit_trail/
└── policy/
```

### 13.1 Objetivo
Concentrar:
- resolução de perfis
- autorização de comandos do DASH
- registo de ações humanas
- políticas de acesso

---

## 14. Estrutura de testes recomendada

```text
tests/
├── unit/
├── integration/
├── fault_injection/
├── scenarios/
├── fixtures/
└── helpers/
```

### 14.1 Significado

#### `tests/unit/`
Testes por módulo e serviço pequeno.

#### `tests/integration/`
Fluxos entre módulos.

#### `tests/fault_injection/`
Timeouts, perdas de heartbeat, corrupção, divergência, falha de persistência.

#### `tests/scenarios/`
Casos ponta-a-ponta alinhados com os use cases.

#### `tests/fixtures/`
Dados e snapshots de teste.

#### `tests/helpers/`
Utilitários de suporte ao teste.

---

## 15. Estrutura interna recomendada por tipo de teste

```text
tests/
├── unit/
│   ├── core/
│   ├── market/
│   ├── decision/
│   ├── risk/
│   ├── exec/
│   ├── dash/
│   ├── recovery/
│   └── learn/
├── integration/
│   ├── core_market/
│   ├── core_risk/
│   ├── decision_exec/
│   ├── exec_recovery/
│   ├── dash_core/
│   └── full_pipeline/
├── fault_injection/
│   ├── heartbeat/
│   ├── persistence/
│   ├── execution_divergence/
│   └── recovery/
└── scenarios/
    ├── uc_001_startup/
    ├── uc_005_real_execution/
    ├── uc_010_recovery/
    ├── uc_012_kill_switch/
    └── uc_016_rollback/
```

---

## 16. Estrutura de configuração

```text
config/
├── base/
├── environments/
├── secrets_templates/
├── policies/
└── examples/
```

### 16.1 Significado

#### `config/base/`
Configuração comum.

#### `config/environments/`
Perfis por ambiente.
Exemplos:
- `dev`
- `demo`
- `real`
- `test`

#### `config/secrets_templates/`
Templates sem segredos reais.

#### `config/policies/`
Políticas ajustáveis:
- risco
- TTL
- heartbeats
- spread thresholds
- shadow mode
- rollback

#### `config/examples/`
Exemplos de configuração para bootstrap.

### 16.2 Regra obrigatória
Segredos reais não devem ser guardados no repositório.

---

## 17. Estrutura de runtime

```text
runtime/
├── state/
├── logs/
├── exports/
├── backups/
├── cache/
└── tmp/
```

### 17.1 Significado

#### `runtime/state/`
Estado persistido local do CORE e afins.

#### `runtime/logs/`
Logs operacionais locais.

#### `runtime/exports/`
Exportações geradas, por exemplo de logs.

#### `runtime/backups/`
Snapshots e cópias de segurança locais.

#### `runtime/cache/`
Caches transitórias.

#### `runtime/tmp/`
Ficheiros temporários.

### 17.2 Regra obrigatória
`runtime/` não deve ser misturado com `src/` ou `docs/`.

---

## 18. Estrutura de scripts

```text
scripts/
├── bootstrap/
├── run/
├── maintenance/
├── migration/
├── test/
└── packaging/
```

### 18.1 Objetivo
Centralizar scripts operacionais como:
- bootstrap do ambiente
- arranque local
- migrações de persistência
- execução de testes
- empacotamento

---

## 19. Estrutura de ferramentas auxiliares

```text
tools/
├── analyzers/
├── validators/
├── converters/
└── dev_utils/
```

### 19.1 Objetivo
Guardar ferramentas que não fazem parte do runtime principal, mas ajudam em:
- validação de config
- inspeção de logs
- análise de snapshots
- conversões documentais

---

## 20. Convenção recomendada de nomes de ficheiros

### 20.1 Código
- nomes de módulos claros e consistentes
- evitar abreviações obscuras
- nomes previsíveis por domínio

### 20.2 Documentação
- usar nomes estáveis e explícitos
- exemplos:
  - `SDS-300-DECISION.md`
  - `ODIN-TRACEABILITY-MATRIX.md`
  - `ODIN-SDS-MASTER.md`

### 20.3 Testes
- refletir o domínio testado
- exemplos:
  - `test_core_state_machine.py`
  - `test_exec_slippage_guard.py`
  - `test_recovery_inconclusive_path.py`

---

## 21. Regras de boundary entre módulos

### 21.1 Regra obrigatória
Um módulo não deve importar lógica interna de outro módulo quando pode consumir contrato/interface.

### 21.2 Exemplos corretos
- `decision` consome contrato publicado por `core`, não mexe na state machine interna
- `dash` consome publishers/view models, não recalcula bloqueios
- `learn` consome outputs do `decision`, não reimplementa o ciclo decisório

### 21.3 Exemplos errados
- `dash` a recalcular permissões localmente sem o `ActionAvailabilityResolver`
- `exec` a alterar estado global diretamente
- `market` a decidir bloqueio sistémico sem passar pelo CORE/RISK

---

## 22. Regras de entrada no repositório

### 22.1 Antes de criar novo diretório ou módulo
Confirmar:
- já existe domínio adequado?
- isto é realmente transversal?
- isto pertence a runtime e não a source?
- existe documento SDS que justifique este componente?

### 22.2 Regra obrigatória
Não criar pastas genéricas do tipo:
- `misc/`
- `temp/`
- `stuff/`
- `new_code/`

Isso é lixo estrutural.

---

## 23. Ligação entre repositório e documentação

### 23.1 Regra recomendada
Cada módulo principal em `src/` deve poder ser associado a:
- FSD de origem
- SDS correspondente
- requisitos na traceability matrix
- testes na pasta respetiva

### 23.2 Implicação prática
Por exemplo:
- `src/core/` ↔ `SDS-100`, `SDS-110`, `SDS-120`
- `src/market/` ↔ `SDS-200`
- `src/decision/` ↔ `SDS-300`
- `src/risk/` ↔ `SDS-400`
- `src/exec/` ↔ `SDS-500`
- `src/dash/` ↔ `SDS-600`
- `src/recovery/` ↔ `SDS-700`
- `src/learn/` ↔ `SDS-800`

---

## 24. Estrutura mínima para início real do projeto

Se fores começar com uma base mais pequena, o mínimo aceitável é:

```text
odin/
├── docs/
├── src/
│   ├── core/
│   ├── market/
│   ├── decision/
│   ├── risk/
│   ├── exec/
│   ├── shared/
│   ├── persistence/
│   └── messaging/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── runtime/
│   ├── state/
│   └── logs/
├── config/
├── scripts/
├── README.md
└── CHANGELOG.md
```

### 24.1 Regra
Mesmo num arranque mínimo, `runtime/`, `docs/`, `src/` e `tests/` não devem ser misturados.

---

## 25. Riscos de estrutura já identificados

| Risco | Impacto | Mitigação |
|---|---|---|
| código de múltiplos domínios em `shared/` | alto | manter boundaries rígidos |
| runtime misturado com código | alto | separar `runtime/` |
| documentação solta fora de `docs/` | médio/alto | centralizar artefactos |
| testes apenas no fim | muito alto | criar estrutura de testes desde já |
| scripts espalhados pelo repositório | médio | centralizar em `scripts/` |
| acoplamento direto entre módulos | muito alto | usar contratos e interfaces |

---

## 26. Critérios de aceitação do ODIN-REPO-STRUCTURE

Este documento será considerado suficiente quando:

1. a estrutura de topo do repositório estiver clara;
2. cada domínio técnico principal tiver o seu lugar definido;
3. documentação, código, testes e runtime estiverem separados;
4. a estrutura suportar os SDS atuais sem improviso;
5. a organização prevenir mistura de responsabilidades;
6. existir base clara para inicializar o repositório real.

---

## 27. Próximos passos recomendados

Depois deste documento, os passos mais úteis são:

1. **ODIN-TEST-PLAN.md**
2. **ODIN-IMPLEMENTATION-ROADMAP.md**
3. **README técnico inicial do repositório**
4. **Bootstrap real da árvore no Git**

---

## 28. Conclusão

O **ODIN-REPO-STRUCTURE** é o documento que traduz a arquitetura do Odin em chão físico de engenharia.

Sem ele, a implementação arrisca começar de forma desorganizada, com mistura de domínios e dívida técnica estrutural logo na base.

Com ele, o repositório passa a ter:
- boundaries claros;
- espaço certo para cada coisa;
- ligação direta à documentação;
- base real para começar a construir.

Num projeto como o Odin, estrutura de repositório não é detalhe. É contenção de caos.
