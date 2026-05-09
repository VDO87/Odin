# ODIN-IMPLEMENTATION-ROADMAP
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft inicial de roadmap técnico  
**Tipo de documento:** Roadmap de implementação  
**Objetivo:** Definir a ordem real de construção do Odin, com fases, marcos, dependências, entregáveis, gates de passagem e critérios mínimos de avanço.

---

## 1. Finalidade do documento

O **ODIN-IMPLEMENTATION-ROADMAP** existe para responder a uma pergunta simples e crítica:

**em que ordem concreta é que o Odin deve ser implementado para não nascer torto?**

O projeto já tem:
- baseline funcional;
- SDS principais;
- matriz de rastreabilidade;
- modelo técnico do CORE;
- estrutura de repositório.

O que faltava era uma tradução disto para:
- ordem de execução;
- marcos técnicos;
- MVP real;
- critérios de passagem entre fases;
- prioridades de implementação.

Sem este documento, o risco é claro:
- começar por partes visualmente apelativas;
- atrasar o núcleo técnico;
- criar dívida estrutural cedo demais;
- perder o controlo do que é essencial vs. secundário.

---

## 2. Princípios do roadmap

### 2.1 Núcleo antes de interface
O Odin deve ganhar coluna vertebral antes de ganhar aparência.

### 2.2 Segurança antes de autonomia
Nenhum automatismo deve entrar antes de existirem:
- estado global coerente;
- risco mínimo;
- persistência crítica;
- recovery básico.

### 2.3 Demo antes de real
O pipeline completo deve funcionar e ser observável em demo antes de qualquer operação real.

### 2.4 Resiliência antes de evolução
Não faz sentido pôr o LEARN a mexer no sistema antes de estabilizar CORE, EXEC e RECOVERY.

### 2.5 Cada fase tem gate de saída
Nenhuma fase deve ser dada por concluída só porque “parece funcionar”.

---

## 3. Visão geral das fases

| Fase | Nome | Objetivo central |
|---|---|---|
| F0 | Fundação de repositório | preparar estrutura, convenções e base técnica |
| F1 | Núcleo operacional | implementar CORE, persistência e interfaces centrais |
| F2 | Consciência operacional | implementar MARKET e RISK mínimos |
| F3 | Decisão e execução demo | fechar pipeline decisão -> intenção -> execução simulada |
| F4 | Supervisão e recovery | implementar DASH mínimo e RECOVERY funcional |
| F5 | Endurecimento técnico | fault-injection, bloqueios, slippage, divergência, observabilidade |
| F6 | Operação real controlada | preparar passagem conservadora a modo real |
| F7 | Evolução controlada | implementar LEARN com shadow, promoção e rollback |

---

## 4. Fase F0 — Fundação de repositório

### 4.1 Objetivo
Preparar a base física do projeto para desenvolvimento disciplinado.

### 4.2 Entregáveis mínimos
- repositório organizado conforme `ODIN-REPO-STRUCTURE.md`
- diretórios-base criados
- documentação colocada em `docs/`
- convenções iniciais definidas
- ficheiros-base:
  - `README.md`
  - `CHANGELOG.md`
  - `.gitignore`
  - `config/examples/`
  - `runtime/` preparado mas excluído conforme necessário

### 4.3 Dependências
- `ODIN-REPO-STRUCTURE.md`
- `ODIN-SDS-MASTER.md`

### 4.4 Gate de saída
A F0 só termina quando:
- o repositório tiver boundaries claros;
- a documentação estiver organizada;
- não existir mistura entre `src/`, `runtime/`, `docs/` e `tests/`.

---

## 5. Fase F1 — Núcleo operacional

### 5.1 Objetivo
Implementar a espinha dorsal mínima do sistema.

### 5.2 Documentos base
- `SDS-100 — CORE`
- `SDS-110 — CORE-PERSISTENCE`
- `SDS-120 — CORE-INTERFACES`
- `ODIN-CORE-STATE-AND-EVENT-MODEL`
- `ODIN-TRACEABILITY-MATRIX`

### 5.3 Entregáveis mínimos
- state machine do CORE
- enum de estados, modos e eventos
- event queue / serialização básica
- transition guards
- block manager
- heartbeat supervisor
- publisher do estado global
- persistência mínima:
  - state snapshot
  - kill flag
  - block vector
  - runtime marker

### 5.4 Resultados esperados
- arranque limpo
- shutdown controlado
- rejeição de transições inválidas
- kill persistente bloqueia arranque
- heartbeat timeout força bloqueio por falha

### 5.5 Gate de saída
A F1 só termina quando:
- o CORE tiver estado global coerente;
- o kill persistente sobreviver a restart;
- o vetor de bloqueios funcionar;
- houver testes básicos de transição.

---

## 6. Fase F2 — Consciência operacional

### 6.1 Objetivo
Dar ao sistema noção séria de mercado e risco antes de decidir ou executar.

### 6.2 Documentos base
- `SDS-200 — MARKET`
- `SDS-400 — RISK`

### 6.3 Entregáveis mínimos
- módulo MARKET mínimo
- classificação de:
  - market ready / invalid / degraded / closed
- spread adaptativo
- filtro de notícias / janela macro crítica
- módulo RISK mínimo
- bloqueio por risco
- kill-switch funcional
- envelopes por modo

### 6.4 Resultados esperados
- sistema sabe quando o mercado é inutilizável
- sistema sabe quando risco impede operação
- kill e bloqueio por risco entram no CORE corretamente

### 6.5 Gate de saída
A F2 só termina quando:
- `MARKET -> CORE` publicar prontidão coerente;
- `RISK -> CORE` conseguir bloquear;
- o sistema não tratar feed vivo como condição operacional normal quando spread/latência/contexto forem maus.

---

## 7. Fase F3 — Decisão e execução demo

### 7.1 Objetivo
Fechar o pipeline lógico ponta-a-ponta, ainda sem risco real.

### 7.2 Documentos base
- `SDS-300 — DECISION`
- `SDS-500 — EXEC`

### 7.3 Entregáveis mínimos
- ciclo decisório mínimo
- uma ou poucas táticas iniciais
- scoring mínimo auditável
- intenção operacional com:
  - `intent_id`
  - `decision_cycle_id`
  - `ttl_ms`
  - `expires_at`
  - `max_slippage`
- EXEC em modo demo
- confirmação/rejeição simulada
- `EV-INTENTION-EXPIRED`
- tratamento de slippage e divergência básica

### 7.4 Resultados esperados
- pipeline completo:
  `MARKET -> DECISION -> RISK -> EXEC`
- sistema consegue:
  - não operar;
  - operar em demo;
  - rejeitar por risco;
  - expirar intenção;
  - registar racional.

### 7.5 Gate de saída
A F3 só termina quando:
- houver operação demo ponta-a-ponta;
- nenhuma intenção expirada seja executada;
- o rational e logging do DECISION forem reconstruíveis;
- divergência e slippage tenham comportamento definido.

---

## 8. Fase F4 — Supervisão e recovery

### 8.1 Objetivo
Tornar o sistema supervisionável e resiliente.

### 8.2 Documentos base
- `SDS-600 — DASH`
- `SDS-700 — RECOVERY`

### 8.3 Entregáveis mínimos
- dashboard mínimo funcional
- estado global visível
- painéis resumidos dos módulos
- alarm center
- block vector panel
- start/stop/pause/resume
- entrada em manutenção com perfil
- logs consultáveis
- exportação mínima
- RECOVERY com:
  - classificação de incidente
  - reconstrução de estado
  - reconciliação
  - saída segura

### 8.4 Resultados esperados
- operador consegue perceber porque o sistema não opera
- reinício inesperado entra em recovery
- recovery não regressa a `ACTIVE`
- bloqueios manuais e kill persistente mantêm precedência

### 8.5 Gate de saída
A F4 só termina quando:
- o dashboard refletir o estado oficial do CORE;
- o recovery conseguir tratar pelo menos:
  - reinício inesperado
  - perda de heartbeat
  - divergência executória
- o sistema conseguir sair de recovery apenas para `IDLE` ou `MONITORING`.

---

## 9. Fase F5 — Endurecimento técnico

### 9.1 Objetivo
Transformar o Odin de protótipo funcional em sistema robusto.

### 9.2 Entregáveis mínimos
- fault-injection tests
- testes de:
  - timeout de heartbeat
  - falha de persistência
  - divergência de execução
  - kill persistente
  - bloqueio manual
  - recovery inconclusivo
- observabilidade melhorada
- métricas de saúde mínimas
- runbook técnico inicial
- melhoria das mensagens de erro e reason codes

### 9.3 Resultados esperados
- o sistema falha de forma previsível;
- os alarmes e logs ajudam em vez de atrapalhar;
- a operação demo fica dura o suficiente para diagnóstico sério.

### 9.4 Gate de saída
A F5 só termina quando:
- houver cobertura de fault-injection nos fluxos críticos;
- o sistema entrar em fail-safe por omissão;
- o comportamento em incidente for repetível.

---

## 10. Fase F6 — Operação real controlada

### 10.1 Objetivo
Preparar e introduzir operação real de forma extremamente conservadora.

### 10.2 Pré-condições obrigatórias
- F1 a F5 concluídas
- pipeline demo estabilizado
- recovery básico validado
- logs e alarmes operacionais já úteis
- kill persistente e block vector já confiáveis

### 10.3 Entregáveis mínimos
- configuração separada para `REAL`
- permissões endurecidas no DASH
- restrições de risco mais fortes
- confirmação explícita de modo real
- execução real controlada e auditável
- exportação mínima para análise pós-operação

### 10.4 Regra obrigatória
A entrada em real não é uma “feature”. É uma mudança de regime.  
Tem de ser tratada como gate de segurança.

### 10.5 Gate de saída
A F6 só termina quando:
- houver execução real controlada sem desvio grave;
- o operador conseguir interromper e bloquear com confiança;
- o sistema mantiver integridade de logs, recovery e risco.

---

## 11. Fase F7 — Evolução controlada

### 11.1 Objetivo
Permitir melhoria do sistema sem perder governabilidade.

### 11.2 Documento base
- `SDS-800 — LEARN`

### 11.3 Entregáveis mínimos
- recolha de histórico
- propostas formais
- snapshots
- shadow mode
- promoção controlada
- rollback
- publicação de versão ativa

### 11.4 Regra obrigatória
O LEARN não deve tocar produção real sem:
- snapshot válido
- política de aprovação
- shadow mode, quando exigido
- rollback funcional

### 11.5 Gate de saída
A F7 só termina quando:
- o sistema conseguir promover e reverter versões sem caos;
- toda alteração relevante for auditável;
- a baseline antiga continuar recuperável.

---

## 12. MVP técnico real do Odin

### 12.1 Definição
O **MVP técnico** do Odin não é “ter um dashboard e uns sinais”.  
É ter o pipeline mínimo seguro e observável.

### 12.2 MVP técnico mínimo
Inclui:
- CORE funcional
- persistência crítica
- MARKET mínimo
- RISK mínimo
- DECISION mínimo
- EXEC demo
- DASH mínimo
- RECOVERY mínimo

### 12.3 O que o MVP técnico deve conseguir
- arrancar com segurança
- saber se pode ou não pode operar
- decidir de forma básica e auditável
- executar em demo
- bloquear por risco
- falhar para estado seguro
- recuperar de um reinício inesperado simples
- mostrar ao operador o estado real

---

## 13. Fases que não devem ser invertidas

### 13.1 Proibições práticas
Não fazer:
- DASH antes de CORE/RISK/EXEC mínimos
- LEARN antes de DECISION/EXEC/RECOVERY estabilizados
- REAL antes de demo robusta
- shadow mode antes de snapshots e rollback
- interface assistida avançada antes de estado global sólido

### 13.2 Regra de ouro
Primeiro:
- fundação
- segurança
- observabilidade
- resiliência

Só depois:
- evolução
- automatização mais agressiva
- refinamento secundário

---

## 14. Dependências críticas entre fases

| Fase | Depende fortemente de |
|---|---|
| F1 | F0 |
| F2 | F1 |
| F3 | F1 + F2 |
| F4 | F1 + F3 |
| F5 | F1 + F2 + F3 + F4 |
| F6 | F1 a F5 |
| F7 | F1 a F6 (ou pelo menos F1 a F5 bem maduras) |

---

## 15. Critérios de passagem entre fases

### 15.1 Regra transversal
Cada fase só pode fechar se cumprir:
- entregáveis mínimos
- gate técnico
- rastreabilidade mínima atualizada
- testes mínimos associados

### 15.2 Regra obrigatória
Nenhuma fase deve ser considerada “feita” com base apenas em opinião visual ou sensação de progresso.

---

## 16. Ligação com a traceability matrix

### 16.1 Regra
A `ODIN-TRACEABILITY-MATRIX` deve ser atualizada por fase.

### 16.2 Utilização prática
No fim de cada fase, deve ser possível marcar requisitos como:
- `PLANNED`
- `IN_PROGRESS`
- `IMPLEMENTED`
- `TESTED`
- `VALIDATED`

### 16.3 Implicação
O roadmap não substitui a rastreabilidade.
O roadmap ordena a execução.
A matriz prova cobertura.

---

## 17. Riscos de implementação já identificados

| Risco | Impacto | Fase crítica |
|---|---|---|
| começar pelo dashboard | alto | F0/F1 |
| não endurecer persistência cedo | muito alto | F1 |
| decidir sem mercado/risco robusto | muito alto | F2/F3 |
| demo sem recovery | alto | F4 |
| ir para real demasiado cedo | muito alto | F6 |
| introduzir LEARN antes de estabilidade base | muito alto | F7 |
| ignorar fault injection | muito alto | F5 |

---

## 18. Entregáveis recomendados a seguir ao roadmap

Depois deste roadmap, os documentos mais úteis são:

1. **ODIN-TEST-PLAN.md**
2. **ODIN-RUNBOOK-v0.1.md**
3. **README do repositório com arranque real**
4. **Bootstrap da árvore do projeto no Git**

---

## 19. Critérios de aceitação do ODIN-IMPLEMENTATION-ROADMAP

Este documento será considerado suficiente quando:

1. a ordem real de implementação estiver clara;
2. cada fase tiver objetivo, entregáveis e gate de saída;
3. existir definição de MVP técnico;
4. as dependências entre fases estiverem explícitas;
5. o roadmap impedir inversões perigosas de prioridade;
6. o documento servir de guia real para começar a construção.

---

## 20. Conclusão

O **ODIN-IMPLEMENTATION-ROADMAP** é a peça que transforma a arquitetura documental do Odin em sequência de construção real.

Sem ele, a implementação corre o risco de ser conduzida por impulso, conveniência ou entusiasmo momentâneo.  
Com ele, o projeto ganha:
- ordem;
- prioridades;
- gates;
- controlo de maturidade;
- uma definição clara do que é “mínimo seguro” antes de avançar.

Num sistema como o Odin, roadmap não é burocracia. É contenção de erro estratégico.
