# SDS-120 — CORE-INTERFACES
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Interfaces técnicas do CORE com MARKET, RISK, DECISION, EXEC, RECOVERY, DASH, LEARN e camada de persistência.

---

## 1. Finalidade do documento

Este documento define os **contratos técnicos de interface** do módulo **CORE** do Odin.

O objetivo é especificar, de forma clara e implementável:
- que mensagens o CORE recebe;
- que mensagens o CORE publica;
- que informação é obrigatória em cada interface;
- que semântica operacional cada interface deve respeitar;
- que comportamentos são permitidos, proibidos ou condicionados.

Sem este documento, o risco é elevado:
- módulos a enviar estados implícitos;
- semântica diferente para o mesmo evento;
- integrações frágeis e difíceis de testar;
- dependências ocultas entre módulos.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- interfaces técnicas do CORE com módulos internos do Odin;
- contratos lógicos de eventos e mensagens;
- payloads mínimos;
- garantias e expectativas funcionais por interface;
- regras de erro, timeout e fail-safe por interface;
- classificação de interfaces síncronas e assíncronas;
- responsabilidades do CORE enquanto consumidor e produtor de estado.

### 2.2 Excluído
Este documento não inclui:
- especificação de protocolo físico definitivo;
- binding para tecnologia específica (REST, gRPC, ZeroMQ, etc.);
- API externa do broker;
- design visual do dashboard;
- estruturas completas de base de dados.

---

## 3. Objetivos técnicos

As interfaces do CORE deverão garantir, no mínimo:

1. **Semântica estável**  
   O mesmo tipo de evento deve significar a mesma coisa em todo o sistema.

2. **Contratos mínimos explícitos**  
   Nenhum módulo crítico deve depender de campos implícitos ou “combinados por hábito”.

3. **Fail-safe por interface**  
   Ausência de resposta, payload inválido ou timeout em interface crítica deve resultar em comportamento conservador.

4. **Separação entre comando e observação**  
   Interfaces de controlo humano, estado global e execução operacional não devem ser confundidas.

5. **Testabilidade**  
   Cada interface deve poder ser validada com testes unitários, de integração e fault-injection.

---

## 4. Modelo geral de interface

### 4.1 Tipos canónicos de interface
O CORE deverá lidar, no mínimo, com quatro classes de interface:

| Tipo | Natureza | Exemplo |
|---|---|---|
| `command` | comando explícito | `EV-START`, `EV-STOP`, `EV-PAUSE` |
| `state_update` | atualização de estado resumido | MARKET publica `EV-MARKET-READY` |
| `critical_event` | evento crítico com impacto de estado | `EV-KILL-ACTIVE`, `EV-EXEC-DIVERGENCE` |
| `query/read-model` | leitura de estado publicado | DASH consulta estado global consolidado |

### 4.2 Regra obrigatória
O CORE não deve interpretar uma atualização informativa como se fosse comando de transição, salvo regra explícita.

---

## 5. Envelope base de mensagem

Todas as interfaces orientadas a eventos do CORE deverão respeitar o seguinte envelope-base:

| Campo | Obrigatório | Descrição |
|---|---|---|
| `event_id` | Sim | identificador único do evento |
| `event_type` | Sim | tipo de evento canónico |
| `source_module` | Sim | módulo emissor |
| `timestamp_utc` | Sim | timestamp UTC |
| `severity` | Sim | severidade canónica |
| `correlation_id` | Recomendado | correlação entre eventos |
| `payload_schema_version` | Sim | versão do payload |
| `payload` | Sim | conteúdo específico |

### 5.1 Regras obrigatórias
- O CORE deve rejeitar mensagens sem `event_type`.
- O CORE deve rejeitar mensagens sem `source_module`.
- O CORE deve rejeitar mensagens com `payload_schema_version` não suportada.
- O CORE deve registar rejeições de contrato como evento técnico rastreável.

---

## 6. Tipos de interface do CORE

O CORE atua como:

| Papel | Descrição |
|---|---|
| `consumer` | consome eventos e estados vindos de outros módulos |
| `publisher` | publica estado global consolidado e eventos de transição |
| `gatekeeper` | valida se ações podem prosseguir em função do estado global |
| `supervisor` | monitoriza liveness, bloqueios e coerência |

---

## 7. Interface CORE <-> MARKET

### 7.1 Finalidade
Permitir ao CORE saber:
- se o mercado está funcionalmente utilizável;
- se o feed está íntegro;
- se existe contexto mínimo para promoção de estado;
- se existe degradação suficiente para travar ou bloquear.

### 7.2 Mensagens mínimas consumidas pelo CORE

| Evento | Obrigatório | Finalidade |
|---|---|---|
| `EV-MARKET-READY` | Sim | contexto mínimo válido |
| `EV-MARKET-DEGRADED` | Sim | feed/contexto degradado |
| `EV-MARKET-INVALID` | Sim | contexto não utilizável |
| `EV-MARKET-CLOSED` | Recomendado | mercado fechado |
| `EV-MARKET-HOSTILE` | Recomendado | contexto hostil |
| `EV-MARKET-NEWS-GUARD` | Recomendado | janela macro crítica |
| `EV-HB-OK` / `EV-HB-TIMEOUT` | Sim | liveness do MARKET |

### 7.3 Payload mínimo relevante do MARKET

| Campo | Obrigatório |
|---|---|
| `market_state` | Sim |
| `context_class` | Sim |
| `feed_integrity_state` | Sim |
| `last_valid_update_utc` | Sim |
| `instrument_scope` | Recomendado |
| `spread_state` | Recomendado |
| `news_guard_active` | Recomendado |

### 7.4 Regras obrigatórias
- O CORE não deve promover o sistema a `READY` ou `ACTIVE` sem sinal compatível do MARKET.
- `EV-MARKET-READY` não basta se houver bloqueio superior ativo.
- `EV-MARKET-DEGRADED` pode impedir promoção ou causar regressão para `MONITORING`.

### 7.5 Timeout/fail-safe
Se o MARKET deixar de publicar heartbeat ou contexto válido dentro da janela suportada:
- o CORE deve degradar ou bloquear por falha, conforme gravidade;
- nunca deve assumir mercado válido por silêncio.

---

## 8. Interface CORE <-> RISK

### 8.1 Finalidade
Permitir ao CORE saber se a operação:
- é permitida;
- está restrita;
- está bloqueada;
- está sob kill-switch.

### 8.2 Mensagens mínimas consumidas pelo CORE

| Evento | Obrigatório | Finalidade |
|---|---|---|
| `EV-RISK-ALLOW` | Sim | risco permissivo |
| `EV-RISK-RESTRICT` | Sim | risco restritivo |
| `EV-RISK-BLOCK` | Sim | bloqueio por risco |
| `EV-KILL-ACTIVE` | Sim | kill-switch ativo |
| `EV-KILL-CLEARED` | Recomendado | kill limpo |
| `EV-HB-OK` / `EV-HB-TIMEOUT` | Sim | liveness do RISK |

### 8.3 Payload mínimo relevante do RISK

| Campo | Obrigatório |
|---|---|
| `risk_state` | Sim |
| `allowance_class` | Sim |
| `kill_active` | Sim |
| `dominant_risk_reason` | Recomendado |
| `risk_snapshot_ref` | Recomendado |

### 8.4 Regras obrigatórias
- `EV-KILL-ACTIVE` tem precedência máxima.
- O CORE deve persistir e refletir bloqueio de risco no vetor de bloqueios.
- `EV-KILL-CLEARED` não pode limpar kill persistente sem validação/autorização adicional.

### 8.5 Timeout/fail-safe
Se o RISK não responder ou perder liveness:
- o CORE deve assumir “não operar”;
- em contexto crítico, deve convergir para `BLOCKED_FAULT`.

---

## 9. Interface CORE <-> DECISION

### 9.1 Finalidade
Permitir ao CORE:
- saber o estado resumido do motor de decisão;
- receber eventos de decisão relevantes para rastreabilidade;
- garantir que DECISION respeita o estado global publicado.

### 9.2 Mensagens mínimas consumidas pelo CORE

| Evento | Obrigatório | Finalidade |
|---|---|---|
| `decision_state_update` | Recomendado | estado resumido de decisão |
| `decision_cycle_closed` | Recomendado | fecho de ciclo decisório |
| `decision_error` | Recomendado | erro decisório |
| `EV-HB-OK` / `EV-HB-TIMEOUT` | Recomendado | liveness do DECISION |

### 9.3 Payload mínimo relevante do DECISION

| Campo | Obrigatório |
|---|---|
| `decision_state` | Sim |
| `decision_cycle_id` | Recomendado |
| `decision_output` | Recomendado |
| `selected_tactic_id` | Opcional |
| `intent_id` | Opcional |
| `reason_summary` | Recomendado |

### 9.4 Regras obrigatórias
- O CORE não depende do DECISION para decidir o seu próprio estado global.
- O DECISION depende do estado do CORE; o inverso é apenas observacional e de rastreabilidade.
- Intenção operacional emitida não altera o estado global do CORE por si só.

---

## 10. Interface CORE <-> EXEC

### 10.1 Finalidade
Permitir ao CORE reagir a:
- submissão de execução;
- confirmação;
- rejeição;
- expiração de intenção;
- slippage excessivo;
- divergência crítica.

### 10.2 Mensagens mínimas consumidas pelo CORE

| Evento | Obrigatório | Finalidade |
|---|---|---|
| `EV-EXEC-SUBMITTED` | Recomendado | submissão iniciada |
| `EV-EXEC-CONFIRMED` | Recomendado | execução confirmada |
| `EV-EXEC-REJECTED` | Recomendado | rejeição normal |
| `EV-EXEC-REJECTED-SLIPPAGE` | Recomendado | rejeição por slippage |
| `EV-INTENTION-EXPIRED` | Sim | expiração observável |
| `EV-EXEC-DIVERGENCE` | Sim | divergência crítica |
| `EV-HB-OK` / `EV-HB-TIMEOUT` | Sim | liveness do EXEC |

### 10.3 Payload mínimo relevante do EXEC

| Campo | Obrigatório |
|---|---|
| `execution_state` | Sim |
| `intent_id` | Recomendado |
| `decision_cycle_id` | Recomendado |
| `execution_result` | Recomendado |
| `slippage_value` | Opcional |
| `divergence_class` | Opcional |
| `reconciliation_confidence` | Opcional |

### 10.4 Regras obrigatórias
- `EV-EXEC-DIVERGENCE` deve ser tratado como evento crítico com potencial entrada em recovery.
- `EV-INTENTION-EXPIRED` deve ser observável no DASH e nos logs do CORE.
- O CORE não deve deduzir “executado” a partir de `submitted`.

### 10.5 Timeout/fail-safe
Se o EXEC perder liveness em contexto operacional:
- o CORE deve convergir para estado seguro;
- especialmente se existir risco de ordens pendentes ou divergência.

---

## 11. Interface CORE <-> RECOVERY

### 11.1 Finalidade
Permitir ao CORE delegar reconstrução e validação de estado após incidentes.

### 11.2 Mensagens mínimas consumidas pelo CORE

| Evento | Obrigatório | Finalidade |
|---|---|---|
| `EV-RECOVERY-START` | Sim | início de recovery |
| `EV-RECOVERY-OK` | Sim | recovery validado |
| `EV-RECOVERY-OK-RESTRICTED` | Recomendado | recovery validado com restrições |
| `EV-RECOVERY-FAIL` | Sim | recovery falhado |
| `EV-RECOVERY-INTERVENTION-REQUIRED` | Recomendado | intervenção humana necessária |
| `EV-HB-OK` / `EV-HB-TIMEOUT` | Recomendado | liveness do RECOVERY |

### 11.3 Payload mínimo relevante do RECOVERY

| Campo | Obrigatório |
|---|---|
| `recovery_state` | Sim |
| `recovery_result` | Sim |
| `reconciliation_confidence` | Recomendado |
| `intervention_required` | Recomendado |
| `recovery_snapshot_ref` | Recomendado |
| `reason_summary` | Recomendado |

### 11.4 Regras obrigatórias
- `EV-RECOVERY-OK` não pode provocar ida direta a `ACTIVE`.
- `EV-RECOVERY-FAIL` deve manter ou agravar bloqueio.
- Recovery não limpa bloqueio manual nem kill persistente automaticamente.

---

## 12. Interface CORE <-> DASH

### 12.1 Finalidade
Permitir:
- comandos humanos controlados para o CORE;
- leitura do estado oficial do sistema pelo operador.

### 12.2 Comandos mínimos recebidos do DASH

| Evento | Obrigatório | Finalidade |
|---|---|---|
| `EV-START` | Sim | arranque |
| `EV-STOP` | Sim | paragem |
| `EV-PAUSE` | Sim | pausa |
| `EV-RESUME` | Sim | retoma/desbloqueio |
| `EV-MODE-CHANGE` | Sim | alteração de modo |
| `EV-MAINTENANCE-ENTER` | Recomendado | entrada em manutenção |
| `EV-MAINTENANCE-EXIT` | Recomendado | saída de manutenção |

### 12.3 Payload mínimo relevante do comando do DASH

| Campo | Obrigatório |
|---|---|
| `operator_id` | Recomendado |
| `requested_action` | Sim |
| `target_mode` | Quando aplicável |
| `maintenance_profile` | Quando aplicável |
| `authorization_context` | Recomendado |
| `reason_text` | Recomendado |

### 12.4 Estado mínimo publicado pelo CORE ao DASH

| Campo | Obrigatório |
|---|---|
| `global_state` | Sim |
| `current_mode` | Sim |
| `dominant_block_reason` | Recomendado |
| `active_block_vector` | Recomendado |
| `last_transition_event` | Recomendado |
| `last_transition_at_utc` | Recomendado |
| `available_actions` | Recomendado |
| `health_summary` | Recomendado |

### 12.5 Regras obrigatórias
- O DASH não decide o estado; apenas comanda e observa.
- O CORE deve validar permissões antes de aceitar comando crítico.
- O CORE deve devolver resultado explícito para comandos rejeitados.

---

## 13. Interface CORE <-> LEARN

### 13.1 Finalidade
Permitir ao CORE saber quando:
- nova versão foi ativada;
- rollback ocorreu;
- aprendizagem falhou ou foi bloqueada.

### 13.2 Mensagens mínimas consumidas pelo CORE

| Evento | Obrigatório | Finalidade |
|---|---|---|
| `EV-LEARN-VERSION-ACTIVATED` | Recomendado | nova versão ativa |
| `EV-LEARN-ROLLBACK` | Recomendado | rollback executado |
| `EV-LEARN-BLOCKED` | Opcional | aprendizagem bloqueada |
| `EV-LEARN-ERROR` | Opcional | erro no processo de aprendizagem |

### 13.3 Payload mínimo relevante do LEARN

| Campo | Obrigatório |
|---|---|
| `version_id` | Quando aplicável |
| `previous_version_id` | Quando aplicável |
| `activation_mode` | Opcional |
| `reason_summary` | Recomendado |

### 13.4 Regras obrigatórias
- O CORE não deve permitir que LEARN altere o estado global de forma direta sem fluxo autorizado.
- Eventos do LEARN são principalmente observacionais ou de governação.

---

## 14. Interface CORE <-> PersistentStateStore

### 14.1 Finalidade
Permitir ao CORE:
- ler estado persistido;
- escrever snapshots críticos;
- validar kill persistente;
- registar runtime marker.

### 14.2 Operações mínimas esperadas

| Operação lógica | Obrigatória |
|---|---|
| `read_runtime_marker` | Sim |
| `write_runtime_marker` | Sim |
| `read_kill_flag` | Sim |
| `write_kill_flag` | Sim |
| `read_core_state_snapshot` | Sim |
| `write_core_state_snapshot` | Sim |
| `read_block_vector_snapshot` | Sim |
| `write_block_vector_snapshot` | Sim |
| `read_recovery_snapshot` | Sim |
| `write_recovery_snapshot` | Sim |
| `validate_persistence_state` | Sim |

### 14.3 Regras obrigatórias
- O backend de persistência deve estar abstraído do CORE.
- Falha de persistência crítica deve ser tratada como evento de risco/falha sistémica.

---

## 15. Classificação de interfaces por mecanismo

### 15.1 Interfaces assíncronas recomendadas
São preferenciais como fluxo base:
- MARKET -> CORE
- RISK -> CORE
- EXEC -> CORE
- RECOVERY -> CORE
- LEARN -> CORE

### 15.2 Interfaces síncronas ou request/response
Podem existir para:
- query de estado do DASH;
- operações de persistência;
- validações locais internas.

### 15.3 Regra recomendada
Mudanças de estado do CORE devem nascer preferencialmente de eventos enfileirados, não de chamadas síncronas encadeadas entre módulos.

---

## 16. Erros de contrato de interface

### 16.1 Tipos mínimos de erro
- `contract_missing_field`
- `contract_invalid_schema_version`
- `contract_invalid_event_type`
- `contract_invalid_source_module`
- `contract_unparseable_payload`
- `contract_timeout`

### 16.2 Regras obrigatórias
- O CORE deve rejeitar contratos inválidos.
- Rejeição de contrato crítico deve gerar log estruturado.
- Erro de contrato repetido em módulo crítico pode escalar para bloqueio por falha.

---

## 17. Timeouts por interface

### 17.1 Regra geral
Cada interface crítica deve ter timeout técnico definido, mesmo que o valor final seja parametrizado em config.

### 17.2 Tabela base

| Interface | Timeout esperado | Fallback |
|---|---|---|
| CORE <- MARKET | configurável | manter/degradar/bloquear |
| CORE <- RISK | configurável | fail-safe: não operar |
| CORE <- EXEC | configurável | bloquear/recovery se contexto crítico |
| CORE <- RECOVERY | configurável | permanecer em recovery ou bloquear |
| CORE <- PersistentStateStore | configurável | bloquear por falha em caso crítico |

### 17.3 Regra obrigatória
Silêncio numa interface crítica não pode ser interpretado como estado saudável.

---

## 18. Regras transversais de segurança operacional

- O CORE não deve aceitar comandos críticos do DASH sem contexto mínimo de autorização.
- O CORE deve persistir estados críticos antes ou imediatamente após certos eventos de elevada severidade.
- O CORE deve publicar estado global apenas após atualização coerente do vetor de bloqueios e do motivo dominante.
- O CORE deve tratar payloads vindos de outros módulos como dados não confiáveis até validação mínima.

---

## 19. Observabilidade por interface

Cada interface crítica deverá suportar, no mínimo, observabilidade sobre:
- número de mensagens recebidas;
- número de mensagens rejeitadas;
- último evento válido;
- último timeout;
- último erro de contrato;
- estado de liveness por módulo.

---

## 20. Testes técnicos mínimos

### 20.1 Unit tests
- validação de payload mínimo por interface;
- rejeição de schema inválido;
- rejeição de `event_type` inválido;
- validação de comandos do DASH;
- parsing do vetor de bloqueios.

### 20.2 Integration tests
- MARKET envia `EV-MARKET-READY` e CORE promove corretamente;
- RISK envia `EV-KILL-ACTIVE` e CORE converge para estado seguro;
- EXEC envia `EV-EXEC-DIVERGENCE` e CORE aciona recovery/bloqueio;
- DASH envia `EV-MAINTENANCE-ENTER` com perfil e CORE aplica comportamento correto;
- PersistentStateStore falha durante evento crítico e CORE entra em comportamento fail-safe.

### 20.3 Fault-injection tests
- payload incompleto de módulo crítico;
- schema version não suportada;
- timeout silencioso do RISK;
- heartbeat perdido do EXEC;
- recovery envia `OK` mas bloqueio manual continua ativo.

---

## 21. Critérios de aceitação

O SDS-120 — CORE-INTERFACES será considerado tecnicamente suficiente quando:

1. cada interface do CORE tiver contrato mínimo claro;
2. os payloads mínimos estiverem definidos;
3. existirem regras explícitas para timeout e erro de contrato;
4. o CORE puder rejeitar mensagens inválidas sem ambiguidade;
5. o DASH puder consumir estado oficial do CORE sem semântica paralela;
6. MARKET, RISK, EXEC e RECOVERY puderem integrar-se com comportamento previsível;
7. a interface de persistência estiver suficientemente abstrata para não contaminar a lógica do CORE.

---

## 22. Dependências e próximos documentos

### 22.1 Dependências principais
- SDS-100 — CORE
- SDS-110 — CORE-PERSISTENCE
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 22.2 Próximos documentos recomendados
1. **SDS-200 — MARKET**
2. **SDS-400 — RISK**
3. **SDS-500 — EXEC**
4. **SDS-600 — DASH**

---

## 23. Conclusão

O SDS-120 fecha a gramática de integração do CORE com o resto do Odin.

Sem estas interfaces definidas, cada módulo tenderia a integrar-se com suposições próprias, produzindo um sistema frágil, difícil de testar e vulnerável a ambiguidades semânticas.

Com este documento, o CORE passa a ter contratos técnicos mínimos, previsíveis e auditáveis com cada módulo crítico.

Num sistema deste tipo, uma interface mal definida é uma falha latente à espera do primeiro incidente real.
