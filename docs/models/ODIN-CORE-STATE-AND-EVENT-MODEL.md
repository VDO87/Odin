# ODIN-CORE-STATE-AND-EVENT-MODEL

**Versão:** 0.1  
**Estado:** Draft técnico intermédio  
**Tipo de documento:** Modelo técnico de estados e eventos  
**Objetivo:** Definir o modelo formal do CORE para estados globais, modos, eventos, precedências, bloqueios, heartbeats e contratos-base de mensagem, servindo de ponte entre o FSD consolidado e o SDS-100.

---

## 1. Finalidade do documento

Este documento fixa o **modelo técnico canónico** do CORE do Odin para:

- estados globais;
- modos operacionais;
- eventos transversais;
- eventos críticos de módulos;
- precedência de eventos;
- vetor de bloqueios;
- envelope-base de mensagens;
- regras de transição;
- modelo de heartbeat/liveness.

A sua função é reduzir ambiguidades antes da implementação, evitando que o SDS ou o código inventem semânticas novas para estados e eventos que já devem estar estabilizados.

---

## 2. Âmbito

### 2.1 Incluído
Este documento inclui:
- enum funcional/técnico de estados;
- enum funcional/técnico de modos;
- enum de eventos do CORE;
- classificação de severidade;
- payload-base de mensagens;
- regras de precedência;
- matriz-base de transições;
- estrutura de bloqueios ativos;
- heartbeat de módulos críticos.

### 2.2 Excluído
Este documento não inclui:
- implementação concreta em linguagem específica;
- base de dados final;
- APIs externas específicas;
- desenho visual do DASH;
- lógica detalhada de scoring e execução broker-specific.

---

## 3. Convenções

### 3.1 Prefixos obrigatórios
- `ST` — estado global
- `MD` — modo operacional
- `EV` — evento transversal
- `BLK` — bloqueio
- `HB` — heartbeat / liveness
- `SEV` — severidade

### 3.2 Regras
- Todo evento processado pelo CORE deve ter tipo explícito.
- Toda transição de estado deve referir `from_state`, `event_type` e `to_state`.
- Bloqueios coexistentes devem ser mantidos no vetor de bloqueios ativos.
- O motivo dominante é apenas uma projeção do vetor, não substitui o vetor.

---

## 4. Estados globais canónicos

| Código | Nome canónico | Descrição resumida |
|---|---|---|
| ST-00 | OFFLINE | Sistema desligado ou sem ciclo ativo |
| ST-10 | STARTUP | Arranque e validação inicial |
| ST-20 | IDLE | Sistema ativo, estabilizado, sem operação em curso |
| ST-30 | MONITORING | Observação e validação de contexto |
| ST-40 | READY | Pronto para operar, sujeito ao modo |
| ST-50 | ACTIVE | Operação ativa permitida |
| ST-60 | PAUSED | Suspensão temporária controlada |
| ST-70 | BLOCKED_RISK | Bloqueio por risco |
| ST-80 | BLOCKED_FAULT | Bloqueio por falha/integridade |
| ST-90 | ERROR | Erro não resolvido |
| ST-100 | RECOVERY | Reconstrução e validação de estado |
| ST-110 | TRAINING | Treino/aprendizagem |
| ST-120 | MAINTENANCE | Intervenção técnica controlada |

### 4.1 Regras obrigatórias
- Só pode existir um estado global ativo em cada instante.
- Estados bloqueados não podem transitar diretamente para `ST-50`.
- `ST-100` não pode transitar diretamente para `ST-50`.
- `ST-10` não pode transitar diretamente para `ST-50`.

---

## 5. Modos operacionais canónicos

| Código | Nome canónico | Descrição resumida |
|---|---|---|
| MD-10 | OBSERVATION | Observação sem execução real |
| MD-20 | DEMO | Execução simulada / não real |
| MD-30 | REAL | Operação real |
| MD-40 | TRAINING | Aprendizagem e análise |
| MD-50 | MAINTENANCE | Intervenção técnica |

### 5.1 Regras obrigatórias
- O modo é distinto do estado.
- Só pode existir um modo ativo em cada instante.
- O modo `MD-30` exige as validações mais restritivas do sistema.
- `MD-50` deve forçar restrição de execução conforme o perfil de manutenção ativo.

---

## 6. Severidades canónicas

| Código | Nome | Uso típico |
|---|---|---|
| SEV-10 | DEBUG | Diagnóstico local |
| SEV-20 | INFO | Evento normal e rastreável |
| SEV-30 | WARN | Degradação, restrição ou anomalia não crítica imediata |
| SEV-40 | ERROR | Falha relevante ou rejeição crítica |
| SEV-50 | CRITICAL | Kill, divergência séria, perda de módulo crítico, recovery inconclusivo |

---

## 7. Envelope base de mensagem/evento

Todo evento processado pelo CORE deverá respeitar o seguinte envelope mínimo.

| Campo | Obrigatório | Descrição |
|---|---|---|
| `event_id` | Sim | ID único do evento |
| `event_type` | Sim | Tipo de evento |
| `source_module` | Sim | Módulo emissor |
| `timestamp_utc` | Sim | Timestamp UTC |
| `severity` | Sim | Severidade canónica |
| `correlation_id` | Recomendado | ID de correlação multi-evento |
| `state_ref` | Opcional | Snapshot ou referência de estado |
| `payload` | Sim | Dados específicos do evento |

### 7.1 Regras obrigatórias
- Eventos sem `event_type` são inválidos.
- Eventos sem `source_module` são inválidos.
- Eventos sem `timestamp_utc` não podem ser considerados confiáveis.
- `payload` deve ser serializável e auditável.

---

## 8. Eventos canónicos do CORE

### 8.1 Eventos de controlo humano ou sistémico

| Código | Evento | Origem típica |
|---|---|---|
| EV-START | pedido de arranque | DASH / sistema |
| EV-STOP | pedido de paragem | DASH / sistema |
| EV-PAUSE | pedido de pausa | DASH / política |
| EV-RESUME | pedido de retoma/desbloqueio | DASH / sistema |
| EV-MODE-CHANGE | alteração de modo | DASH / política |
| EV-MAINTENANCE-ENTER | entrada em manutenção | DASH |
| EV-MAINTENANCE-EXIT | saída de manutenção | DASH |

### 8.2 Eventos de mercado

| Código | Evento | Origem |
|---|---|---|
| EV-MARKET-READY | mercado/contexto mínimo válido | MARKET |
| EV-MARKET-INVALID | mercado/contexto inválido | MARKET |
| EV-MARKET-DEGRADED | feed ou contexto degradado | MARKET |
| EV-MARKET-CLOSED | mercado fechado | MARKET |
| EV-MARKET-HOSTILE | contexto hostil | MARKET |
| EV-MARKET-NEWS-GUARD | janela macro crítica | MARKET |

### 8.3 Eventos de risco

| Código | Evento | Origem |
|---|---|---|
| EV-RISK-ALLOW | risco permissivo | RISK |
| EV-RISK-RESTRICT | risco restritivo | RISK |
| EV-RISK-BLOCK | bloqueio por risco | RISK |
| EV-KILL-ACTIVE | kill-switch ativo | RISK |
| EV-KILL-CLEARED | kill-switch limpo | RISK / ação autorizada |

### 8.4 Eventos de execução

| Código | Evento | Origem |
|---|---|---|
| EV-EXEC-SUBMITTED | submissão iniciada | EXEC |
| EV-EXEC-CONFIRMED | execução confirmada | EXEC |
| EV-EXEC-REJECTED | rejeição de execução | EXEC |
| EV-EXEC-REJECTED-SLIPPAGE | rejeição por slippage | EXEC |
| EV-EXEC-DIVERGENCE | divergência crítica | EXEC |
| EV-INTENTION-EXPIRED | intenção expirada antes da execução | EXEC |

### 8.5 Eventos de recovery

| Código | Evento | Origem |
|---|---|---|
| EV-RECOVERY-START | início de recovery | RECOVERY / CORE |
| EV-RECOVERY-OK | recovery validado | RECOVERY |
| EV-RECOVERY-OK-RESTRICTED | recovery validado com restrições | RECOVERY |
| EV-RECOVERY-FAIL | recovery falhado | RECOVERY |
| EV-RECOVERY-INTERVENTION-REQUIRED | intervenção humana obrigatória | RECOVERY |

### 8.6 Eventos de heartbeat/liveness

| Código | Evento | Origem |
|---|---|---|
| EV-HB-OK | heartbeat recebido e válido | módulo crítico / supervisor |
| EV-HB-DELAYED | heartbeat atrasado | HeartbeatSupervisor |
| EV-HB-TIMEOUT | heartbeat excedeu timeout | HeartbeatSupervisor |

### 8.7 Eventos de falha

| Código | Evento | Origem |
|---|---|---|
| EV-FAULT-BLOCK | bloqueio por falha | CORE / módulo crítico |
| EV-ERROR | erro não resolvido | módulo crítico |
| EV-PERSISTENCE-INCONSISTENT | estado persistido inconsistente | CORE / RECOVERY |
| EV-MODULE-UNAVAILABLE | módulo obrigatório indisponível | CORE |

---

## 9. Precedência de eventos

### 9.1 Ordem canónica
Da maior para a menor precedência:

1. `EV-KILL-ACTIVE`
2. `EV-FAULT-BLOCK`
3. `EV-HB-TIMEOUT`
4. `EV-EXEC-DIVERGENCE`
5. `EV-RECOVERY-START`
6. `EV-RISK-BLOCK`
7. `EV-STOP`
8. `EV-PAUSE`
9. `EV-MAINTENANCE-ENTER`
10. `EV-MODE-CHANGE`
11. `EV-MARKET-INVALID`
12. `EV-MARKET-DEGRADED`
13. `EV-MARKET-READY`
14. `EV-RESUME`
15. eventos informativos (`EV-HB-OK`, `EV-EXEC-SUBMITTED`, etc.)

### 9.2 Regra crítica
Se dois eventos concorrentes implicarem destinos incompatíveis, prevalece o de maior precedência.

### 9.3 Exemplo
- `EV-RESUME` + `EV-HB-TIMEOUT`  
  resultado: convergência para **ST-80 — BLOCKED_FAULT**

---

## 10. Vetor de bloqueios ativos

### 10.1 Estrutura mínima

| Campo | Descrição |
|---|---|
| `block_id` | identificador do bloqueio |
| `block_type` | manual / risk / fault / recovery / kill |
| `source_module` | origem |
| `created_at` | timestamp |
| `severity` | severidade |
| `clear_condition` | condição de limpeza |
| `manual_clear_required` | booleano |

### 10.2 Tipos canónicos de bloqueio

| Código | Tipo |
|---|---|
| BLK-10 | manual |
| BLK-20 | risk |
| BLK-30 | fault |
| BLK-40 | administrative / maintenance |
| BLK-50 | recovery_pending |
| BLK-60 | kill_persistent |

### 10.3 Regra de precedência de bloqueios
Da maior para a menor:
1. `BLK-60 kill_persistent`
2. `BLK-10 manual`
3. `BLK-30 fault`
4. `BLK-50 recovery_pending`
5. `BLK-20 risk`
6. `BLK-40 administrative`

### 10.4 Regras obrigatórias
- O CORE deve manter simultaneamente:
  - `dominant_block_reason`
  - `active_block_vector[]`
- Um bloqueio manual não pode ser limpo por recovery automático.
- Um kill persistente não pode desaparecer após reboot.
- O sistema só sai de estado bloqueado quando os bloqueios impeditivos compatíveis deixarem de existir.

---

## 11. Heartbeat e liveness

### 11.1 Módulos críticos mínimos
- MARKET
- RISK
- EXEC

### 11.2 Módulos recomendados
- DECISION
- RECOVERY

### 11.3 Payload mínimo do heartbeat

| Campo | Obrigatório |
|---|---|
| `module_id` | Sim |
| `timestamp_utc` | Sim |
| `module_state` | Sim |
| `mode_context` | Recomendado |
| `sequence_number` | Recomendado |
| `health_flag` | Sim |

### 11.4 Regras obrigatórias
- Ausência de heartbeat acima de `heartbeat_timeout_ms` ou `heartbeat_timeout_cycles` gera `EV-HB-TIMEOUT`.
- `EV-HB-TIMEOUT` de módulo crítico deve provocar convergência para estado seguro.
- Heartbeat é requisito de liveness, não substitui validação funcional profunda.

---

## 12. Intenção operacional — contrato mínimo relevante para o CORE

Embora a intenção operacional pertença ao fluxo DECISION/EXEC, o CORE depende do seu modelo para coerência de eventos.

### 12.1 Campos mínimos relevantes

| Campo | Obrigatório |
|---|---|
| `intent_id` | Sim |
| `decision_cycle_id` | Sim |
| `created_at` | Sim |
| `ttl_ms` | Sim |
| `expires_at` | Sim |
| `market_snapshot_ref` | Sim |
| `risk_snapshot_ref` | Sim |
| `max_slippage` | Sim |

### 12.2 Regras obrigatórias
- `EV-INTENTION-EXPIRED` deve ser gerado pelo EXEC se a intenção expirar antes da submissão.
- O CORE deve tratar este evento como falha observável de oportunidade, não como execução rejeitada genérica.
- Expiração repetitiva pode ser tratada como indicador técnico de latência excessiva.

---

## 13. Perfis de manutenção

### 13.1 Perfis canónicos

| Código lógico | Nome | Comportamento resumido |
|---|---|---|
| MNT-10 | maintenance_soft | bloqueia novas intenções e execuções; mantém estado protegido existente |
| MNT-20 | maintenance_managed_exit | bloqueia novas entradas; permite saída controlada |
| MNT-30 | maintenance_hard_exit | força saída máxima permitida |

### 13.2 Regra obrigatória
Se o operador não escolher explicitamente um perfil, o fallback é:
- `MNT-10 maintenance_soft`

---

## 14. Matriz-base de transições do CORE

| From | Evento | Guard principal | To | Tipo |
|---|---|---|---|---|
| ST-00 OFFLINE | EV-START | config mínima válida | ST-10 STARTUP | manual |
| ST-10 STARTUP | EV-KILL-ACTIVE / kill persistido | kill presente | ST-80 BLOCKED_FAULT ou ST-120 MAINTENANCE | automática |
| ST-10 STARTUP | EV-RECOVERY-START | encerramento não limpo / incerteza | ST-100 RECOVERY | automática |
| ST-10 STARTUP | EV-MARKET-READY ou condição de arranque limpo | módulos mínimos válidos | ST-30 MONITORING ou ST-20 IDLE | condicionada |
| ST-20 IDLE | EV-MODE-CHANGE | modo permitido | ST-20 IDLE | manual interna |
| ST-20 IDLE | EV-MAINTENANCE-ENTER | ação autorizada | ST-120 MAINTENANCE | manual |
| ST-20 IDLE | EV-START lógico / política operacional | dependências mínimas | ST-30 MONITORING | manual/condicionada |
| ST-30 MONITORING | EV-MARKET-READY | risco sem bloqueio, modo compatível | ST-40 READY | automática |
| ST-30 MONITORING | EV-MARKET-INVALID | mercado inválido | ST-30 MONITORING | interna / sem promoção |
| ST-30 MONITORING | EV-RISK-BLOCK | bloqueio ativo | ST-70 BLOCKED_RISK | automática |
| ST-30 MONITORING | EV-FAULT-BLOCK / EV-HB-TIMEOUT | falha crítica | ST-80 BLOCKED_FAULT | automática |
| ST-40 READY | evento interno de ativação operacional | guards completos válidos | ST-50 ACTIVE | condicionada |
| ST-40 READY | EV-PAUSE | ação autorizada | ST-60 PAUSED | manual |
| ST-40 READY | EV-RISK-BLOCK | bloqueio ativo | ST-70 BLOCKED_RISK | automática |
| ST-40 READY | EV-FAULT-BLOCK | falha crítica | ST-80 BLOCKED_FAULT | automática |
| ST-50 ACTIVE | EV-PAUSE | ação autorizada | ST-60 PAUSED | manual |
| ST-50 ACTIVE | EV-RISK-BLOCK | bloqueio ativo | ST-70 BLOCKED_RISK | automática |
| ST-50 ACTIVE | EV-FAULT-BLOCK / EV-HB-TIMEOUT | falha crítica | ST-80 BLOCKED_FAULT | automática |
| ST-50 ACTIVE | EV-MAINTENANCE-ENTER | perfil de manutenção escolhido | ST-120 MAINTENANCE | manual condicionada |
| ST-60 PAUSED | EV-RESUME | sem bloqueios impeditivos | ST-30 MONITORING | manual |
| ST-70 BLOCKED_RISK | EV-RESUME | bloqueio de risco limpo e sem bloqueios superiores | ST-30 MONITORING | manual |
| ST-70 BLOCKED_RISK | EV-FAULT-BLOCK | falha superveniente | ST-80 BLOCKED_FAULT | automática |
| ST-80 BLOCKED_FAULT | EV-RECOVERY-START | incidente recuperável | ST-100 RECOVERY | automática/condicionada |
| ST-80 BLOCKED_FAULT | EV-MAINTENANCE-ENTER | ação autorizada | ST-120 MAINTENANCE | manual |
| ST-100 RECOVERY | EV-RECOVERY-OK | reconciliação válida | ST-20 IDLE ou ST-30 MONITORING | automática |
| ST-100 RECOVERY | EV-RECOVERY-OK-RESTRICTED | reconciliação parcial | ST-30 MONITORING | automática |
| ST-100 RECOVERY | EV-RECOVERY-FAIL | recuperação falhada | ST-80 BLOCKED_FAULT ou ST-90 ERROR | automática |
| ST-110 TRAINING | EV-STOP | pedido de paragem | ST-00 OFFLINE | manual |
| ST-120 MAINTENANCE | EV-MAINTENANCE-EXIT | sem bloqueios impeditivos | ST-20 IDLE | manual |

### 14.1 Transições proibidas
As seguintes transições devem ser tratadas como proibidas:
- `ST-00 -> ST-50`
- `ST-10 -> ST-50`
- `ST-70 -> ST-50`
- `ST-80 -> ST-50`
- `ST-90 -> ST-50`
- `ST-100 -> ST-50`

---

## 15. Guards canónicos

### 15.1 Lista base de guards
- `guard_config_valid`
- `guard_mode_compatible`
- `guard_market_ready`
- `guard_risk_not_blocked`
- `guard_no_kill_active`
- `guard_no_fault_block`
- `guard_recovery_validated`
- `guard_manual_action_authorized`
- `guard_block_vector_compatible`
- `guard_maintenance_profile_defined`

### 15.2 Regra obrigatória
Uma transição condicionada só pode ocorrer se **todos os guards obrigatórios** dessa transição forem verdadeiros.

---

## 16. Regras de arranque endurecido

### 16.1 O arranque deve verificar obrigatoriamente:
- integridade mínima da configuração;
- existência de `kill_flag` persistida;
- consistência do estado persistido;
- bloqueios persistidos;
- disponibilidade mínima dos componentes críticos do CORE;
- necessidade de recovery.

### 16.2 Regra crítica
Sem passar esta validação, o sistema não pode progredir para `ST-20`, `ST-30`, `ST-40` ou `ST-50`.

---

## 17. Regras de saída de estados bloqueados

### 17.1 Regras obrigatórias
- saída de `ST-70` exige limpeza do bloqueio de risco e ausência de bloqueios superiores;
- saída de `ST-80` exige recovery ou validação equivalente;
- bloqueio manual exige ação manual explícita;
- kill persistente exige limpeza autorizada e auditável;
- recovery validado nunca implica desbloqueio manual automático.

---

## 18. Regras de observabilidade obrigatória

O CORE deve tornar observável, pelo menos:
- estado global atual;
- modo atual;
- última transição;
- evento causador da última transição;
- motivo dominante de bloqueio;
- vetor completo de bloqueios ativos;
- health/liveness dos módulos críticos;
- kill persistente ativo;
- recovery pendente ou inconclusivo.

---

## 19. Casos de validação mínima deste modelo

O modelo deve permitir validar, no mínimo:
1. arranque limpo;
2. arranque com kill persistente;
3. bloqueio por ausência de heartbeat do MARKET;
4. bloqueio manual coexistente com recovery validado;
5. intenção expirada antes de submissão;
6. rejeição por slippage excessivo;
7. transição para manutenção com perfil `maintenance_soft`;
8. tentativa de `EV-RESUME` com bloqueio manual ainda ativo;
9. tentativa de transição proibida para `ST-50`.

---

## 20. Conclusão

O presente documento fixa a gramática técnica mínima do CORE do Odin:
- que estados existem;
- que eventos existem;
- como concorrem;
- que bloqueios coexistem;
- que transições são válidas;
- que guards devem ser avaliados.

Sem este modelo, o SDS e o código correriam o risco de derivar semânticas diferentes para o mesmo sistema.  
Com este modelo, o CORE passa a ter uma base formal, rastreável e suficientemente rígida para evolução técnica controlada.
