# ODIN-ENGINEERING-RULES
## Projeto Odin

**Versão:** 0.1  
**Estado:** Baseline inicial de engenharia  
**Tipo de documento:** Regras de governação técnica  
**Objetivo:** Fixar as decisões mínimas de stack, configuração, persistência, testes e convenções de implementação para arrancar F0/F1 do Odin sem ambiguidade de engenharia.

---

## 1. Finalidade do documento

Este documento fecha as decisões técnicas mínimas que os SDS propositadamente deixaram em aberto enquanto a arquitetura ainda estava a ser consolidada.

O objetivo não é congelar o futuro do projeto.  
O objetivo é impedir que a implementação inicial nasça com decisões ad hoc sobre:

- linguagem e runtime;
- estrutura de projeto;
- persistência crítica;
- configuração;
- contratos de dados;
- testes e qualidade base.

---

## 2. Decisões técnicas iniciais

### 2.1 Stack principal
- **Linguagem:** Python 3.12
- **Layout do projeto:** repositório orientado a domínios sob `src/`
- **Gestão de projeto:** `pyproject.toml`
- **Configuração:** TOML versionado em `config/`
- **Testes:** `pytest`
- **Lint/format/checks estáticos:** `ruff` e `mypy`

### 2.2 Persistência inicial
- **Estado estruturado crítico do CORE:** SQLite local
- **Logs funcionais append-only:** ficheiros `jsonl`
- **Snapshots de recovery e artefactos transitórios:** diretórios sob `runtime/`

### 2.3 Memória auxiliar opcional
- **Camada opcional:** MemPalace local como sidecar de memória auxiliar
- **Uso permitido:** recall histórico, consulta assistida, apoio ao LEARN e contexto advisory do DECISION
- **Uso proibido:** estado autoritativo do CORE, gating de RISK, intenção executiva oficial, recovery state oficial
- **Regra de congelamento:** sempre que memória auxiliar influenciar um ciclo decisório ou proposta do LEARN, os resultados usados devem ser congelados no snapshot oficial desse ciclo
### 2.4 Política de dependências
- standard library por defeito sempre que suficiente;
- dependências de runtime novas exigem justificação explícita;
- contratos de fronteira podem usar `pydantic` quando saírem dos docs para código;
- evitar frameworks distribuídos ou assíncronos pesados no MVP.

---

## 3. Regras de implementação do MVP

### 3.1 CORE serializado
No MVP, toda mutação de estado global do CORE deve passar por um pipeline serial único.

### 3.2 Fail-safe por defeito
Ausência de liveness, persistência inconsistente ou contrato inválido devem resultar em bloqueio conservador ou regressão de estado, nunca em promoção otimista.

### 3.3 Contratos primeiro
Nenhum adaptador externo deve introduzir payloads próprios fora dos contratos canónicos definidos em SDS-100, SDS-110 e SDS-120.

### 3.4 Runtime separado do código
Ficheiros em `runtime/` não são fonte de verdade do repositório.  
São artefactos operacionais locais.

### 3.5 Memória auxiliar não autoritativa
Mesmo quando o MemPalace estiver ativo:
- o `CORE` continua a ser a autoridade única de estado;
- `SDS-110` continua a ser a autoridade de persistência crítica;
- `DECISION` continua determinístico relativamente ao snapshot congelado do ciclo;
- falha da memória auxiliar não pode impedir o Odin de convergir para estado seguro.

---

## 4. Convenções de configuração

### 4.1 Fonte de configuração
- defaults seguros no código;
- exemplos versionados em `config/examples/`;
- valores sensíveis fora do repositório;
- nenhum segredo real em ficheiros versionados.

### 4.2 Estrutura mínima esperada
- `core`
- `market`
- `risk`
- `exec`
- `memory`
- `observability`
- `runtime`

### 4.3 Regra obrigatória
Configuração inválida deve impedir progressão operacional no arranque.

---

## 5. Convenções de código

### 5.1 Organização
- domínios sob `src/core`, `src/market`, `src/decision`, `src/risk`, `src/exec`, `src/dash`, `src/recovery`, `src/learn`
- contratos e tipos transversais sob `src/shared`
- persistência sob `src/persistence`
- mensageria interna sob `src/messaging`

### 5.2 Regras mínimas
- sem lógica crítica escondida em utilitários genéricos;
- nomes de módulos e contratos alinhados com SDS/FSD;
- side effects isolados em camadas explícitas;
- read-models separados das mutações de estado.

### 5.3 Regra obrigatória
Se um comportamento tiver impacto em estado global, risco, recovery ou execução, deve ser localizável num módulo de domínio explícito.

---

## 6. Contratos e tipos

### 6.1 Contratos canónicos prioritários
- `core_event_envelope`
- `global_state_snapshot`
- `active_block_vector`
- `module_heartbeat`
- `execution_intent`
- `recovery_result`
- `memory_advisory_context`

### 6.2 Política
- contratos partilhados devem ser versionados;
- breaking changes exigem revisão dos docs e da matriz de rastreabilidade;
- enums de estados, modos, eventos e bloqueios são parte da baseline técnica e não devem ser redefinidos por módulo.

---

## 7. Regras de testes

### 7.1 Tooling inicial
- `pytest` para execução de suites;
- `tests/unit`, `tests/integration`, `tests/scenarios`, `tests/fault_injection`;
- doubles e simuladores sob `tests/fixtures` e `tests/simulators` quando surgirem.

### 7.2 Regra obrigatória
Qualquer funcionalidade ligada a:
- transições do CORE;
- kill persistente;
- bloqueios manuais;
- expiração de intenção;
- divergência;
- recovery

deve nascer acompanhada do respetivo teste mínimo.

---

## 8. Regras de observabilidade

### 8.1 Logging funcional
- eventos críticos em formato estruturado;
- UTC obrigatório;
- correlação por `correlation_id` ou equivalente;
- severidade explícita.

### 8.2 Artefactos de runtime
- `runtime/logs/`
- `runtime/state/`
- `runtime/backups/`
- `runtime/memory/`

### 8.3 Regra obrigatória
Observabilidade mínima é parte do MVP técnico.  
Não é pós-processamento opcional.

---

## 9. Critérios de mudança desta baseline

Esta baseline pode evoluir, mas alterações aos seguintes pontos exigem revisão explícita dos documentos de governação:

- linguagem principal;
- formato base de configuração;
- backend de persistência crítica do CORE;
- papel da memória auxiliar na arquitetura;
- modelo de concorrência do CORE;
- estrutura de diretórios do repositório;
- toolchain principal de testes e qualidade.

---

## 10. Conclusão

O **ODIN-ENGINEERING-RULES** fecha o mínimo que faltava entre documentação e implementação:

- stack escolhida;
- política de persistência inicial;
- regras de configuração;
- convenções de código;
- e baseline de testes/qualidade.

Com este documento, F0 e F1 podem arrancar sem decisões estruturais improvisadas no meio da implementação.
