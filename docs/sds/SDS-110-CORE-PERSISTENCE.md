# SDS-110 — CORE-PERSISTENCE
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Persistência técnica do CORE, checkpoints, kill flag, vetor de bloqueios, snapshots de recovery e integridade do estado persistido.

---

## 1. Finalidade do documento

Este documento define a especificação técnica da camada de **persistência do CORE** do Odin.

Se o SDS-100 define a lógica técnica do núcleo, o SDS-110 define **como o estado mínimo crítico do CORE deve sobreviver a reinícios, falhas de energia, crashes, recovery e bloqueios persistentes**.

A persistência do CORE não existe para armazenar “histórico bonito”. Existe para garantir:

- arranque seguro;
- continuidade controlada;
- recovery fiável;
- kill-switch persistente;
- rastreabilidade mínima dos estados críticos;
- integridade do vetor de bloqueios.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- modelo de persistência mínima obrigatória do CORE;
- estrutura dos registos persistidos;
- snapshots/checkpoints de estado;
- kill flag persistente;
- vetor de bloqueios persistido;
- marcadores de encerramento limpo / não limpo;
- snapshots de recovery;
- regras de escrita, leitura e validação;
- integridade e consistência do estado persistido;
- retenção mínima de artefactos críticos;
- abstração técnica de armazenamento.

### 2.2 Excluído
Este documento não inclui:
- histórico completo de trading;
- logs de negócio detalhados;
- persistência profunda do DECISION ou LEARN;
- desenho final de replicação distribuída;
- backups externos/cloud.

---

## 3. Objetivos técnicos

A persistência do CORE deverá garantir, no mínimo:

1. **Sobrevivência a reboot e crash**  
   O estado crítico do CORE deve poder ser reconstituído após reinício inesperado.

2. **Kill-switch persistente**  
   Um kill ativo não pode desaparecer com restart de processo ou sistema operativo.

3. **Recuperação orientada por evidência**  
   O recovery deve ter contexto bastante para reconstruir estado com confiança.

4. **Integridade mínima verificável**  
   O CORE deve conseguir detetar estado persistido incompleto, corrompido ou incoerente.

5. **Escrita de checkpoints críticos**  
   Eventos de alta severidade devem ser acompanhados de persistência consistente do estado.

6. **Abstração do backend de armazenamento**  
   O CORE não deve ficar acoplado a um backend específico de persistência.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-100 — CORE
- FSD-400 — RISK
- FSD-700 — RECOVERY
- FSD consolidado v0.5
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| Kill persistente deve sobreviver a reboot | FSD-400 / v0.4 / v0.5 | `kill_flag_store` + validação obrigatória no arranque |
| O CORE deve manter vetor de bloqueios ativos | FSD-100 / v0.4 / v0.5 | persistência de `active_block_vector` |
| O recovery deve usar estado persistido | FSD-700 | snapshots/checkpoints de recovery |
| O sistema deve detetar encerramento não limpo | FSD-700 | `shutdown_marker` + `last_clean_shutdown` |
| O arranque deve validar estado persistido | FSD-100 / SDS-100 | `startup_persistence_validator` |

---

## 5. Princípios técnicos obrigatórios

### 5.1 Persistir o mínimo crítico, não tudo cegamente
A camada de persistência do CORE deve guardar o necessário para segurança operacional e recovery, não todo o universo de dados do sistema.

### 5.2 Escrita crítica antes de conveniência
Em eventos críticos, a persistência deve privilegiar consistência sobre velocidade bruta.

### 5.3 Estado persistido não é verdade absoluta
Tudo o que estiver persistido deve ser validado no arranque e, quando necessário, reconciliado com estado observado.

### 5.4 Kill e bloqueios críticos têm prioridade
Artefactos que impeçam operação indevida devem ser persistidos de forma mais robusta do que estados meramente informativos.

### 5.5 Leituras devem ser seguras e explícitas
Se o estado persistido estiver incompleto ou inconsistente, o CORE deve entrar em fluxo conservador.

---

## 6. Modelo técnico de armazenamento

### 6.1 Abstração obrigatória
A persistência do CORE deverá ser exposta ao resto do sistema através de uma interface lógica, por exemplo:

- `PersistentStateStore`

### 6.2 Responsabilidades mínimas da interface
A interface de persistência deverá suportar, no mínimo:

- leitura do estado global persistido;
- escrita de checkpoint de estado;
- leitura/escrita do kill flag;
- leitura/escrita do vetor de bloqueios;
- leitura/escrita do snapshot de recovery;
- marcação de encerramento limpo;
- marcação de arranque em curso;
- validação da integridade mínima dos artefactos persistidos.

### 6.3 Backends tecnicamente aceitáveis na fase inicial
Aceitam-se, na primeira fase:
- SQLite local;
- ficheiros estruturados com escrita atómica;
- KV store local resiliente.

### 6.4 Recomendação
Para a fase inicial do Odin, a opção tecnicamente mais equilibrada é:

- **SQLite local para estado estruturado**
- **ficheiro separado ou tabela dedicada para kill flag**
- **append-only logs fora do escopo principal do estado do CORE**

---

## 7. Artefactos persistidos obrigatórios

A camada de persistência do CORE deverá suportar, no mínimo, os seguintes artefactos.

### 7.1 Global state snapshot
Snapshot da última visão consistente do estado global do sistema.

### 7.2 Kill flag persistente
Flag persistente e auditável que impede arranque operacional normal enquanto não for limpa autorizadamente.

### 7.3 Active block vector snapshot
Instantâneo do vetor de bloqueios ativos, incluindo bloqueio dominante e metadados mínimos.

### 7.4 Shutdown marker
Marcador que permita distinguir:
- encerramento limpo;
- encerramento não limpo;
- arranque interrompido.

### 7.5 Recovery snapshot
Snapshot com evidência mínima útil para reconstrução de estado após incidente.

### 7.6 Last critical transition record
Registo mínimo da última transição crítica do CORE.

---

## 8. Estrutura mínima do estado persistido

### 8.1 Entidade: `core_state_snapshot`

| Campo | Tipo lógico | Obrigatório | Descrição |
|---|---|---|---|
| `snapshot_id` | string | Sim | ID único do snapshot |
| `created_at_utc` | datetime | Sim | timestamp do snapshot |
| `global_state` | enum | Sim | estado global persistido |
| `current_mode` | enum | Sim | modo persistido |
| `dominant_block_reason` | string | Não | motivo dominante |
| `last_transition_event` | string | Não | último evento de transição |
| `last_transition_at_utc` | datetime | Não | timestamp da última transição |
| `readiness_status` | string | Não | estado resumido de prontidão |
| `persistence_version` | string | Sim | versão do schema persistido |
| `is_consistent` | boolean | Sim | flag de consistência produzida pelo writer |

### 8.2 Regras obrigatórias
- Cada snapshot deve ser identificável univocamente.
- O snapshot deve conter versão de schema para suportar evolução futura.
- `is_consistent=false` deve ser tratado como sinal de risco no arranque.

---

## 9. Estrutura mínima do kill flag persistente

### 9.1 Entidade: `core_kill_flag`

| Campo | Tipo lógico | Obrigatório | Descrição |
|---|---|---|---|
| `kill_id` | string | Sim | ID único do kill persistido |
| `is_active` | boolean | Sim | flag ativa/inativa |
| `activated_at_utc` | datetime | Sim | timestamp de ativação |
| `activated_by` | string | Não | origem humana ou módulo |
| `source_module` | string | Sim | origem funcional |
| `reason_code` | string | Sim | motivo resumido |
| `reason_text` | string | Não | descrição auditável |
| `manual_clear_required` | boolean | Sim | deve ser verdadeiro por defeito |
| `cleared_at_utc` | datetime | Não | timestamp de limpeza |
| `cleared_by` | string | Não | origem da limpeza |
| `clear_audit_ref` | string | Não | referência auditável |

### 9.2 Regras obrigatórias
- Um kill ativo deve sobreviver a reboot.
- `manual_clear_required` deve ser `true`, salvo política explicitamente diferente aprovada.
- A limpeza do kill deve deixar rasto auditável.
- O arranque deve verificar esta entidade antes de qualquer progressão operacional normal.

---

## 10. Estrutura mínima do vetor de bloqueios persistido

### 10.1 Entidade: `core_block_vector_snapshot`

| Campo | Tipo lógico | Obrigatório | Descrição |
|---|---|---|---|
| `block_snapshot_id` | string | Sim | ID do snapshot do vetor |
| `created_at_utc` | datetime | Sim | timestamp |
| `dominant_block_reason` | string | Sim | motivo dominante |
| `active_block_count` | integer | Sim | número de bloqueios ativos |
| `serialized_block_vector` | json/text | Sim | vetor serializado |
| `has_manual_block` | boolean | Sim | flag derivada |
| `has_kill_block` | boolean | Sim | flag derivada |
| `has_fault_block` | boolean | Sim | flag derivada |

### 10.2 Estrutura mínima de cada bloqueio no vetor

| Campo | Obrigatório |
|---|---|
| `block_id` | Sim |
| `block_type` | Sim |
| `source_module` | Sim |
| `created_at_utc` | Sim |
| `severity` | Sim |
| `manual_clear_required` | Sim |
| `clear_condition` | Não |
| `metadata` | Opcional |

### 10.3 Regras obrigatórias
- O vetor deve preservar todos os bloqueios ativos relevantes.
- O motivo dominante é derivado do vetor e não deve substituí-lo.
- O snapshot do vetor deve ser reavaliado no arranque, não assumido cegamente.

---

## 11. Marcador de encerramento / arranque

### 11.1 Entidade: `core_runtime_marker`

| Campo | Tipo lógico | Obrigatório | Descrição |
|---|---|---|---|
| `marker_id` | string | Sim | ID do marcador |
| `last_startup_at_utc` | datetime | Não | último arranque |
| `startup_in_progress` | boolean | Sim | arranque em curso |
| `last_clean_shutdown` | boolean | Sim | último shutdown limpo |
| `last_shutdown_at_utc` | datetime | Não | último encerramento |
| `last_shutdown_reason` | string | Não | motivo resumido |
| `last_persistence_commit_at_utc` | datetime | Não | último commit consistente |

### 11.2 Regras obrigatórias
- No arranque, `startup_in_progress` deve ser marcado cedo.
- Só no final de um encerramento limpo se deve marcar `last_clean_shutdown=true`.
- Se o sistema reiniciar e encontrar `startup_in_progress=true` ou `last_clean_shutdown=false`, deve assumir potencial encerramento não limpo.

---

## 12. Snapshot de recovery

### 12.1 Entidade: `core_recovery_snapshot`

| Campo | Tipo lógico | Obrigatório | Descrição |
|---|---|---|---|
| `recovery_snapshot_id` | string | Sim | ID único |
| `created_at_utc` | datetime | Sim | timestamp |
| `trigger_event` | string | Sim | evento que motivou o snapshot |
| `global_state_before_incident` | enum | Não | estado conhecido anterior |
| `mode_before_incident` | enum | Não | modo anterior |
| `last_known_intent_id` | string | Não | intenção relevante |
| `last_known_execution_state` | string | Não | estado executório resumido |
| `last_known_market_state` | string | Não | estado resumido do market |
| `last_known_risk_state` | string | Não | estado resumido do risco |
| `block_vector_ref` | string | Não | referência ao snapshot do vetor |
| `notes` | text | Não | observações adicionais |

### 12.2 Regras obrigatórias
- Este snapshot deve ser escrito em incidentes relevantes ou antes de transições críticas para recovery, quando tecnicamente possível.
- O recovery usa este snapshot como ponto de partida, nunca como verdade absoluta.

---

## 13. Política de escrita

### 13.1 Eventos que exigem escrita obrigatória imediata
Os seguintes eventos devem provocar persistência obrigatória ou quase imediata:

- ativação de kill-switch;
- alteração do vetor de bloqueios;
- transição para `ST-80 BLOCKED_FAULT`;
- transição para `ST-100 RECOVERY`;
- transição para `ST-120 MAINTENANCE`;
- limpeza autorizada de kill persistente;
- encerramento limpo;
- arranque em curso.

### 13.2 Eventos que permitem checkpoint normal
Podem seguir política normal de checkpoint:
- transições informativas;
- alterações menores de prontidão;
- heartbeat healthy.

### 13.3 Regra obrigatória
Eventos de severidade `SEV-50 CRITICAL` devem ser acompanhados de persistência de estado coerente.

---

## 14. Política de leitura no arranque

### 14.1 Sequência técnica mínima
No arranque, o CORE deverá:

1. abrir o backend de persistência;
2. ler `core_runtime_marker`;
3. ler `core_kill_flag`;
4. ler `core_state_snapshot`;
5. ler `core_block_vector_snapshot`;
6. validar versões de schema e consistência mínima;
7. determinar se há:
   - kill persistente;
   - encerramento não limpo;
   - bloqueios ativos persistidos;
   - necessidade de recovery.

### 14.2 Regra crítica
A leitura deve ser tratada como fase de validação, não apenas de hidratação passiva de memória.

---

## 15. Validação de integridade

### 15.1 Verificações mínimas
A persistência deverá ser validada no arranque, pelo menos quanto a:

- existência dos artefactos obrigatórios;
- coerência entre `global_state` e `current_mode`;
- coerência entre `dominant_block_reason` e `active_block_vector`;
- coerência entre `kill_flag` e bloqueios ativos;
- versões de schema suportadas;
- timestamps plausíveis;
- snapshots marcados como consistentes.

### 15.2 Resultado da validação
O arranque deverá classificar o estado persistido como:
- `VALID`
- `DEGRADED`
- `INCONSISTENT`
- `UNREADABLE`

### 15.3 Regra obrigatória
Estados `INCONSISTENT` ou `UNREADABLE` devem impedir progressão operacional normal e forçar bloqueio ou recovery.

---

## 16. Comportamento específico do kill persistente

### 16.1 Regra de ouro
Se `core_kill_flag.is_active = true` no arranque:
- o CORE não pode avançar para `IDLE`, `MONITORING`, `READY` ou `ACTIVE`;
- deve convergir para estado bloqueado ou manutenção;
- deve publicar claramente a causa ao DASH.

### 16.2 Limpeza do kill
A limpeza do kill deverá exigir, no mínimo:
- ação autorizada;
- registo de quem limpou;
- timestamp;
- motivo de limpeza;
- persistência imediata da limpeza.

### 16.3 Regra obrigatória
Recovery validado não limpa kill persistente automaticamente.

---

## 17. Backend técnico recomendado para fase inicial

### 17.1 Recomendação
Na fase inicial do Odin, recomenda-se:

- **SQLite** para estado estruturado do CORE;
- **escrita transacional** para snapshots críticos;
- **separação lógica** entre:
  - estado do CORE;
  - logs append-only;
  - backups/exportações.

### 17.2 Tabelas mínimas sugeridas
- `state_snapshots`
- `kill_states`
- `block_vectors`
- `runtime_markers`
- `recovery_snapshots`
- `execution_ledger` (a partir de `schema_version=3`)
- `schema_meta` e `schema_migrations` para governação de versão

### 17.3 Regra
Mesmo usando SQLite, o acesso deve continuar encapsulado por `PersistentStateStore`.

---

## 18. Estratégia de schema versioning

### 18.1 Requisito
Todos os artefactos críticos devem incluir `persistence_version` ou equivalente.

### 18.2 Regras obrigatórias
- O CORE deve recusar ler cegamente artefactos com versão não suportada.
- Migrações futuras devem ser explícitas e auditáveis.
- `persistence_version` deve ser validado antes de confiar no conteúdo.
- o backend SQLite deve manter `schema_meta` e `schema_migrations` para registar versão atual e migrations aplicadas.
- bases legadas sem metadata de schema devem ser inferidas/migradas sem perda dos registos já persistidos.

### 18.3 Corte atual de migrations

Estado atual mínimo suportado:
- `v1` — schema base do CORE/RECOVERY/LEARN persistido;
- `v2` — histórico auditável de approvals do LEARN;
- `v3` — execution ledger auditável persistido em SQLite.

Regras obrigatórias:
- `initialize()` deve elevar a base para a versão suportada mais recente;
- migrations devem ser idempotentes;
- a versão persistida deve poder ser validada por teste automatizado.

---

## 19. Retenção mínima

### 19.1 Política mínima recomendada
- manter pelo menos o último snapshot consistente do estado;
- manter o último vetor de bloqueios persistido;
- manter o último recovery snapshot;
- manter o histórico de kill ativo/limpo.

### 19.2 Política recomendada
Para facilitar diagnóstico:
- conservar vários snapshots recentes, mas marcar explicitamente o último consistente;
- conservar histórico resumido de kill flags e reversões de bloqueios críticos.

---

## 20. Regras de robustez e atomicidade

### 20.1 Requisitos técnicos mínimos
- escrita de snapshot crítico deve ser atómica ou equivalente;
- o sistema não deve deixar meio snapshot assumido como completo;
- gravação de kill deve ser confirmável;
- escrita do marcador de shutdown deve ser ordenada.

### 20.2 Estratégia recomendada
Em backend baseado em ficheiros:
- escrever para ficheiro temporário;
- fsync/flush;
- rename atómico.

Em SQLite:
- usar transações explícitas para operações críticas.

---

## 21. Interfaces técnicas

### 21.1 Interface mínima da persistência

A abstração `PersistentStateStore` deverá expor, no mínimo, operações equivalentes a:

- `initialize()`
- `validate_integrity()`
- `read_shutdown_marker()`
- `mark_startup_in_progress(startup_id, happened_at_utc)`
- `mark_clean_shutdown(marker_id, happened_at_utc)`
- `read_kill_state()`
- `write_kill_state(kill_state)`
- `read_latest_state_snapshot()`
- `write_state_snapshot(snapshot)`
- `read_latest_block_vector()`
- `write_block_vector(vector)`
- `read_latest_recovery_snapshot()`
- `write_recovery_snapshot(snapshot)`
- `read_latest_execution_ledger_record()`
- `write_execution_ledger_record(record)`
- `list_execution_ledger_records(...)`

No backend SQLite do corte atual, `read_schema_version()` também está disponível para validação explícita de migrations.

### 21.2 Regras obrigatórias
- Falhas de persistência crítica devem ser escaladas ao CORE.
- O CORE deve ser capaz de entrar em estado seguro se o backend falhar em momento crítico.

---

## 22. Testes técnicos mínimos

### 22.1 Unit tests
- serialização/deserialização de snapshots;
- validação de schema version;
- consistência kill flag;
- consistência vetor de bloqueios;
- classificação `VALID/DEGRADED/INCONSISTENT/UNREADABLE`.

### 22.2 Integration tests
- arranque com estado persistido válido;
- arranque com kill persistente ativo;
- arranque com `last_clean_shutdown=false`;
- persistência de bloqueio manual e reavaliação no reboot;
- migração de base legada para a versão atual de schema;
- append e leitura do execution ledger;
- crash durante operação seguido de recovery;
- limpeza autorizada do kill;
- corrupção parcial de snapshot.

### 22.3 Fault-injection tests
- backend indisponível no arranque;
- falha a meio de escrita de checkpoint crítico;
- snapshot com versão não suportada;
- kill ativo sem vetor de bloqueios coerente.

---

## 23. Critérios de aceitação

O SDS-110 — CORE-PERSISTENCE será considerado tecnicamente suficiente quando:

1. o CORE conseguir ler e validar o estado persistido no arranque;
2. o kill persistente sobreviver a reboot;
3. o vetor de bloqueios puder ser preservado e reavaliado;
4. o sistema distinguir encerramento limpo de encerramento não limpo;
5. o recovery tiver snapshot mínimo utilizável;
6. snapshots críticos puderem ser escritos de forma segura;
7. estados persistidos inconsistentes forçarem comportamento conservador;
8. a abstração `PersistentStateStore` permitir trocar backend sem contaminar a lógica do CORE.

---

## 24. Dependências e próximos documentos

### 24.1 Dependências principais
- SDS-100 — CORE
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 24.2 Próximos documentos recomendados
1. **SDS-120 — CORE-INTERFACES**
2. **SDS-200 — MARKET**
3. **SDS-400 — RISK**
4. **SDS-500 — EXEC**

---

## 25. Conclusão

O SDS-110 fecha a camada de memória operacional do CORE.

Sem esta persistência, o Odin perde a capacidade de:
- arrancar com segurança;
- respeitar kill persistente;
- recuperar após falha;
- distinguir o que sabia do que apenas pensa que sabia.

Com esta persistência bem definida, o CORE ganha continuidade real, recovery sério e resistência a incidentes que num sistema deste tipo deixam de ser “exceções” e passam a ser condições normais de projeto.

Num sistema que toca estado crítico e dinheiro real, memória volátil não chega.
