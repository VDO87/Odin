# Odin

Sistema modular para supervisão, decisão, execução controlada, recuperação e evolução disciplinada de estratégias no contexto do projeto Odin.

> Estado atual: **F0 a F7 com corte principal implementado e validado localmente**.  
> O estado do repositório em **2026-04-23** já inclui `LEARN`, persistência auditável, governação negativa, perfis de execução `lite/standard/full`, `DASH-lite` operacional e versionamento/migração de schema no SQLite.

---

## 1. O que é o Odin

O Odin é um sistema desenhado para operar com disciplina técnica em torno de:

- **estado global controlado**
- **validação de mercado**
- **decisão auditável**
- **gestão de risco obrigatória**
- **execução confirmada e reconciliada**
- **recovery após incidente**
- **supervisão humana clara**
- **aprendizagem com governação, shadow mode e rollback**

O objetivo não é “fazer trading automático a qualquer custo”.  
O objetivo é construir uma máquina que **saiba quando pode agir, quando não pode, quando deve parar e como deve recuperar**.

---

## 2. Princípios de engenharia do projeto

O projeto foi estruturado com base em alguns princípios duros:

- **CORE como autoridade única de estado global**
- **fail-safe por defeito**
- **bloqueio manual não sai sozinho**
- **kill-switch persistente**
- **intenção operacional com TTL**
- **execução não é assumida, é confirmada**
- **recovery nunca regressa diretamente a operação ativa**
- **logs críticos tratados como append-only ao nível funcional**
- **aprendizagem só com snapshots, shadow mode e rollback**

---

## 3. Estado atual do projeto

Neste momento, o projeto já não está na fase de arranque.  
A baseline operacional até **F6** está implementada no repositório:

### Implementado e validado
- `CORE` com state machine, guards, block vector, heartbeat, persistência SQLite e fail-safe de persistência
- `MARKET` com ingestão operacional gated por profile, scopes de instrumento/feed, classificação de prontidão e eventos para o `CORE`
- `RISK` mínimo com `ALLOW/RESTRICT/BLOCK/KILL`, kill persistente e política reforçada para `REAL`
- `DECISION` mínimo com scoring auditável, racional e `ExecutionIntent`
- `EXEC` demo e caminho controlado para `REAL`, incluindo slippage, divergência, idempotência e audit trail
- `RECOVERY` mínimo com reconstrução, confiança, reconciliação e saída segura
- `DASH` mínimo com projeção oficial do `CORE`, `DASH-lite` orientado a operação, exportação e gates reforçados para `REAL`
- perfis de execução `lite`, `standard` e `full`, com `lite` por defeito para hardware limitado
- execution ledger auditável persistido no SQLite e migrations de schema com versionamento explícito
- `systemd`/Ubuntu Server com `start_odin.sh`, daemon e instalador
- suites `unit`, `contract`, `integration`, `fault_injection`, `replay` e `scenario` até F6

### Reconhecimento atual
- `ruff check src tests` está verde
- `pytest -q` está verde
- a baseline de F0 a F7 está coerente com o roadmap atual
- `LEARN` já existe no código executável com snapshots, propostas, approval, shadow mode, promoção, rollback, persistência auditável e integração com `CORE`/`DASH`
- o estado operacional atualizado do F7 está em `docs/plans/ODIN-F7-HANDOFF.md`

Isto significa que o projeto está em **fecho controlado do corte F7**, e não em fase de fundação.

---

## 4. Arquitetura macro do sistema

A arquitetura macro do Odin pode ser lida assim:

```text
MARKET -> DECISION -> EXEC
    \        ^         |
     \       |         v
      -> RISK --------> RECOVERY
             ^             ^
             |             |
             +---- CORE ---+
                    |
                    v
                   DASH
                    ^
                    |
                   LEARN
                    ^
                    |
              INTELLIGENCE
```

### Papel de cada módulo
- **CORE** — estado global, bloqueios, modos, precedência, liveness
- **MARKET** — validade do mercado, feed, contexto, spread, janela macro
- **DECISION** — táticas, elegibilidade, scoring, intenção operacional
- **RISK** — limites, bloqueios, kill-switch, envelopes por modo
- **EXEC** — submissão, confirmação, slippage, divergência, reconciliação
- **RECOVERY** — reconstrução de estado, confiança, saída segura
- **DASH** — observação, controlo manual, alarmes, logs, interface assistida
- **LEARN** — propostas, snapshots, shadow mode, promoção, rollback
- **INTELLIGENCE** — camada advisory para cenário/reasoning/memória auxiliar, sem autoridade operacional

---

## 5. Documentação principal

### Funcional
- `docs/fsd/ODIN_FSD_Consolidado_v0_5.md`

### Modelo técnico
- `docs/models/ODIN-CORE-STATE-AND-EVENT-MODEL.md`
- `docs/models/ODIN-AUXILIARY-MEMORY-MODEL.md`

### Rastreabilidade
- `docs/traceability/ODIN-TRACEABILITY-MATRIX.md`

### SDS principais
- `docs/sds/ODIN-SDS-MASTER.md`
- `docs/sds/SDS-100-CORE.md`
- `docs/sds/SDS-110-CORE-PERSISTENCE.md`
- `docs/sds/SDS-120-CORE-INTERFACES.md`
- `docs/sds/SDS-200-MARKET.md`
- `docs/sds/SDS-300-DECISION.md`
- `docs/sds/SDS-400-RISK.md`
- `docs/sds/SDS-500-EXEC.md`
- `docs/sds/SDS-600-DASH.md`
- `docs/sds/SDS-700-RECOVERY.md`
- `docs/sds/SDS-800-LEARN.md`
- `docs/sds/SDS-900-INTELLIGENCE-LAYER.md`

### Planeamento e operação
- `docs/plans/ODIN-IMPLEMENTATION-ROADMAP.md`
- `docs/plans/ODIN-TEST-PLAN.md`
- `docs/plans/ODIN-POST-F7-BACKLOG.md`
- `docs/runbooks/ODIN-RUNBOOK-v0.1.md`
- `docs/runbooks/ODIN-UBUNTU-SERVER-INSTALL.md`
- `docs/runbooks/ODIN-TRADER-CONSOLE-TESTING.md`
- `docs/runbooks/ODIN-CODEBASE-HYGIENE.md`

### Governação
- `docs/governance/ODIN-REPO-STRUCTURE.md`
- `docs/governance/ODIN-ENGINEERING-RULES.md`
- `docs/governance/ODIN-REQUIRED-SOFTWARE.md`

---

## 6. Estrutura recomendada do repositório

Estrutura macro atual/recomendada:

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
└── CHANGELOG.md
```

### Separação importante
- `docs/` -> documentação
- `src/` -> código
- `tests/` -> testes
- `runtime/` -> estado local, logs, backups
- `config/` -> configuração versionada e templates

Não misturar runtime com código.  
Não misturar documentação com scripts ou dados transitórios.

## 6.1 Memória auxiliar

O Odin pode usar uma camada opcional de memória auxiliar, como o MemPalace, para:
- consulta histórica assistida;
- recall de incidentes, decisões e testes anteriores;
- apoio advisory ao DECISION;
- enriquecimento do LEARN.

Regra obrigatória:
- o `CORE` continua a ser a autoridade única de estado;
- a memória auxiliar nunca é fonte oficial de bloqueios, kill, risco, execução ou recovery;
- sempre que memória auxiliar influenciar um ciclo, o contexto usado deve ficar congelado no snapshot oficial desse ciclo.

## 6.2 Intelligence Layer (futuro próximo)

Está especificada uma camada adicional de inteligência advisory em:
- `docs/sds/SDS-900-INTELLIGENCE-LAYER.md`

Boundaries previstos:
- advisory only (não autoritativa);
- sem alteração direta de `CORE`, `RISK`, `EXEC`, `RECOVERY`;
- sem limpeza de bloqueios;
- sem execução de ordens;
- influência em `DECISION`/`LEARN` só via `advisory_snapshot` congelado.

## 6.3 Instalação Ubuntu Server

Para Ubuntu Server, o projeto inclui um instalador único na raiz:

```bash
./INSTALL_ODIN.sh
```

Esse instalador:
- instala os pacotes de sistema necessários;
- por omissão instala em pasta isolada (`$HOME/odin-runtime`) com `config/`, `runtime/`, `.venv/` e `bin/` próprios;
- instala dependências Python;
- prepara `config/odin.local.toml` a partir do profile pedido;
- garante a árvore `runtime/`;
- valida o config final com `odin-validate-config`;
- gera `install-manifest.json` para rastreio de instalação;
- instala a unidade `systemd` `odin-core.service` apenas em modo `--in-place` (ou `--skip-systemd`).

Por omissão, o instalador usa o profile `lite`.
Por omissão usa também modo isolado (`--install-root "$HOME/odin-runtime"`).

Para uma simulação sem alterar o sistema:

```bash
./INSTALL_ODIN.sh --dry-run
```

Para escolher o profile explicitamente:

```bash
./INSTALL_ODIN.sh --profile standard
./INSTALL_ODIN.sh --profile full
```

Para escolher pasta isolada explícita:

```bash
./INSTALL_ODIN.sh --install-root "$HOME/odin-instances/lab-01"
```

Para manter layout legado no repositório:

```bash
./INSTALL_ODIN.sh --in-place
```

Memória auxiliar só é permitida no profile `full`. Para a desligar explicitamente:

```bash
./INSTALL_ODIN.sh --profile full --without-memory
```

Para arrancar manualmente:

```bash
$HOME/odin-runtime/bin/start_odin.sh
```

Para operar via `systemd` em Ubuntu Server:

```bash
sudo systemctl start odin-core.service
sudo systemctl status odin-core.service
```

Logs de ciclo de vida para troubleshooting:
- `runtime/logs/core-daemon-lifecycle.jsonl`
- `runtime/logs/operator-console-lifecycle.jsonl`
- `scripts/odin_trace.sh` para seguir lifecycle + audit operacional em tempo real
  - `scripts/odin_trace.sh --verbose` inclui também `read_query` de polling (status/health/config/external-status)

Purge seguro de instalação isolada:

```bash
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh --dry-run
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh
```

Opções:
- `--remove-config` remove também `config/odin.local.toml`
- `--remove-install` remove toda a pasta de instalação (`ODIN_HOME`)

Guardrails do purge:
- exige `ODIN_HOME` definido;
- recusa `ODIN_HOME` vazio, `/` ou igual à raiz do repositório;
- exige confirmação explícita `PURGE_ODIN`.

## 6.4 Perfis de execução

O runtime suporta três perfis:

- `lite` — profile por defeito; mantém `CORE`, `MARKET`, `RISK`, `DECISION`, `EXEC` e `DASH` mínimo, desliga `LEARN`, shadow mode, memória auxiliar e surface LEARN no `DASH`; no `MARKET` força envelope mínimo com `1` instrumento, `1` feed, `news_guard` desligado, `spread_guard` ativo e sem enriquecimento pesado
- `standard` — mantém o corte operacional sem `LEARN`, com surface de `DASH` standard e sem forçar envelope mínimo do `MARKET` (usa scope e guards configurados)
- `full` — expõe `LEARN`, shadow mode, queries/ações LEARN no `DASH` e pode ativar memória auxiliar

Evolução prevista para inteligência advisory:
- `lite` — desligada por defeito (ou diagnóstico manual);
- `standard` — cenário leve sem LLM contínuo;
- `full` — memória auxiliar + advisory OpenAI + suporte a LEARN.

Regra operacional:
- hardware limitado ou operação inicial: usar `lite`
- promoção para `full` só faz sentido quando houver orçamento para `LEARN`, shadow e memória auxiliar

## 6.5 Enforcement MARKET e DASH-lite

No runtime atual:

- `CoreRuntimeController.ingest_market_sample(...)` é o ponto de entrada oficial de ingestão operacional do `MARKET`;
- o pipeline aplica primeiro o `MarketProfileGate` (scope de instrumento/feed + restrições de guards/enrichment) e só depois adapta para `MarketSampleInput`;
- rejeições de gate (`instrument_scope_rejected`, `feed_scope_rejected`) convergem para estado `NOT_READY` antes da avaliação principal;
- o estado operacional efetivo do `MARKET` fica em `get_market_runtime_status()` e é projetado no `DASH` em `global_state_model.operation_focus.market_runtime`;
- `operation_focus` agrega também o último registo do execution ledger persistido em SQLite (`last_execution`) quando existir.

## 6.6 OPERATOR CONSOLE (corte inicial)

Foi adicionada a superfície inicial do **ODIN Operator Console**:

- `CommandGateway` como ponto único para comandos de operação;
- command surface v1 com endpoints HTTP mínimos;
- confirmação obrigatória para comandos críticos (`stop`, `pause`, `resume`);
- validação/config via preview staged (sem aplicação direta ao runtime neste corte);
- dashboard web local mínimo com polling de 2s e menu lateral operacional.
- **Modo Operador** com cartões legíveis (estado geral, saúde dos módulos, mercado, risco, decisão, execução, eventos recentes);
- **Modo Técnico** com JSON bruto para inspeção detalhada;
- diagnóstico automático no topo com causa provável + ação recomendada quando o Odin não está pronto.
- layout cockpit com:
  - menu lateral segmentado por `OPERAÇÃO`, `EXECUTION`, `PORTFOLIOS`, `ADMINISTRAÇÃO`, `DADOS`, `INTEGRAÇÕES`, `INTELIGÊNCIA`;
  - `EXECUTION` com foco operacional inicial:
    - `MT5 Forex`
    - `XTB Assisted`
    - `Manual Orders`
    - `Execution Ledger`
  - `PORTFOLIOS` por bucket:
    - `Forex Trading`
    - `ETFs`
    - `Ações`
    - `FIRE / Reforma`
    - `3–5 anos`
  - `DADOS` com páginas operacionais:
    - `Market Data`
    - `Economic Calendar`
  - `INTEGRAÇÕES` com placeholders:
    - `Telegram`, `MT5`, `XTB`, `OpenAI`, `Providers`
  - cartões críticos no topo (`Estado`, `Saúde geral`, `Modo`, `Profile`, `Kill`, `Bloqueios`);
  - gráficos leves (sem libs externas): distribuição de health, timeline de estado, severidade de eventos, placeholder de market line.
- polling configurável na UI (`1s`, `2s`, `5s`).
- navegação multi-página por hash:
  - `#dashboard`, `#market`, `#risk`, `#decision`, `#execution`, `#portfolios`, `#logs`, `#config`, `#commands`, `#integrations`, `#intelligence`
  - cada rota mostra apenas a sua página (sem empilhar todo o cockpit).

Entry point:

```bash
$HOME/odin-runtime/bin/start_operator_console.sh
```

Depois abrir no browser:

```text
http://127.0.0.1:8080
```

Endpoints v1:

- `GET /`
- `GET /api/status`
- `GET /api/health`
- `GET /api/logs/recent`
- `GET /api/config`
- `POST /api/commands/pause`
- `POST /api/commands/resume`
- `POST /api/commands/stop`
- `POST /api/logs/export`
- `GET /api/external/status`
- `GET /api/external/quote?symbol=EURUSD`
- `GET /api/external/calendar`
- `GET /api/external/assets/search?q=...`
- `POST /api/external/inject-demo-quote-to-market`
- `POST /api/test/run-decision-cycle`

Uso recomendado:

- abrir em **Modo Operador** para leitura rápida (10s) do estado do Odin;
- usar **Modo Técnico** apenas para análise detalhada e troubleshooting.
- para testes da consola em sandbox, usar apenas `start_operator_console.sh` e não correr `start_odin.sh` em paralelo.
- para validação manual end-to-end (curl + UI), seguir [`docs/runbooks/ODIN-TRADER-CONSOLE-TESTING.md`](/home/vdo/Secretária/Projects_Codex/Odin_Teste/docs/runbooks/ODIN-TRADER-CONSOLE-TESTING.md).

Princípios de segurança aplicados no corte:

- a consola não altera `CORE` fora dos contratos existentes (`CoreDashBridge` + eventos);
- comandos críticos exigem confirmação explícita;
- menu de configuração funciona em modo read-only ou staged;
- preparação de contratos para chat interno, bridge Telegram, advisory OpenAI e adapters `MT5`/`XTB`;
- `MT5` não é exclusivo de Forex por capacidade técnica, mas no Odin inicia como adapter preferencial para `FOREX`/`AUTO_DEMO`/execução curta;
- `XTB` fica posicionado como plataforma ampla (ETFs, ações, CFDs e carteira FIRE/médio-longo prazo) em workflow `TELEGRAM_ASSISTED`/confirmação humana;
- Telegram nunca executa ordens diretamente: comandos passam por `CommandGateway` com confirmação explícita;
- `XTB` real execution fica preparado, mas não ativo neste corte;
- decisões de médio/longo prazo ficam em advisory ou confirmação humana;
- sem execução real de ordens externas nesta entrega.
- `ExternalDataService` é o único ponto de entrada para dados externos (`DemoProvider`, `Alpha Vantage`, `Trading Economics`) com cache TTL e rate limiting;
- `DemoProvider` é obrigatório e funciona sem internet;
- falha de provider externo não pode parar `CORE`, nem tornar provider externo autoridade de `CORE/RISK/EXEC`.
- API keys externas devem ficar em segredos não versionados (`ALPHA_VANTAGE_API_KEY`, `TRADING_ECONOMICS_API_KEY`) ou config local fora de versionamento.
- AnythingLLM/OpenAI ficam fora da baseline operacional deste handoff; tratar qualquer key mencionada em conversa como comprometida e revogar.
- quando for ativar advisory local no futuro, usar segredo fora de versionamento (`ANYTHINGLLM_API_KEY` ou `config/secrets/odin.secrets.toml`).

Limitações atuais do corte:
- sem trading real;
- sem ligação ativa a `MT5`/`XTB` para execução real;
- sem advisory `OpenAI` ativo por defeito;
- `DemoProvider` é fonte por defeito em `profile=lite`.

---

## 7. Ordem recomendada de implementação

A sequência técnica correta é esta:

1. **F0 — Fundação de repositório**
2. **F1 — Núcleo operacional**
3. **F2 — Consciência operacional**
4. **F3 — Decisão e execução demo**
5. **F4 — Supervisão e recovery**
6. **F5 — Endurecimento técnico**
7. **F6 — Operação real controlada**
8. **F7 — Evolução controlada**

### Regra de ouro
Não inverter a ordem por entusiasmo.

Em particular:
- não começar pelo dashboard
- não ir para real cedo
- não introduzir LEARN antes de CORE/EXEC/RECOVERY maduros

---

## 8. MVP técnico do Odin

O **MVP técnico** do Odin não é “ter interface”.  
É ter o pipeline mínimo seguro e observável.

### O MVP técnico inclui
- CORE funcional
- persistência crítica
- MARKET mínimo
- RISK mínimo
- DECISION mínimo
- EXEC demo
- DASH mínimo
- RECOVERY mínimo

### O MVP técnico deve conseguir
- arrancar com segurança
- bloquear por kill persistente
- saber quando o mercado é utilizável
- decidir de forma mínima e auditável
- executar em demo
- falhar para estado seguro
- recuperar de um reinício inesperado simples
- mostrar ao operador o estado real

---

## 9. Política de testes

O projeto já assume que o teste é parte da engenharia, não fase final.

### Camadas mínimas de validação
- **unit tests**
- **integration tests**
- **scenario tests**
- **fault-injection**
- **recovery drills**
- **regression tests**

### Regras importantes
- sem evidência, não está validado
- testar falha é obrigatório
- recovery é primeira classe
- mexer em CORE/EXEC/RECOVERY obriga a regressão

---

## 10. Operação humana

O Odin já tem runbook inicial previsto para:

- arranque
- shutdown
- pausa e retoma
- bloqueio manual
- kill-switch
- recovery
- manutenção
- exportação de logs
- recolha de evidência mínima

A regra operacional mais importante é simples:

> **não limpar bloqueios nem reiniciar cegamente sem perceber a causa.**

---

## 11. Estado recomendado antes de entrar em F7

Antes de avançar com `LEARN`, a baseline que deve estar garantida é:

- F0 a F6 fechadas com evidência local
- `CORE`, `EXEC`, `RECOVERY` e `DASH` estáveis
- gates de `REAL` já conservadores
- traceability, roadmap, plano de testes e runbook já utilizáveis
- exportação auditável e rollback operacional manual já existentes

Neste momento, esta base está montada e validada localmente.

---

## 12. Estado atual do F7

O repositório já não está na fase de "iniciar F7". O corte atual inclui:

- `src/learn/` e contratos partilhados materializados
- snapshots, propostas, approvals, shadow sessions, promoção e rollback implementados
- `DASH` com ações LEARN reais, queries explícitas, `learn_shadow_audit`, `learn_operational_hints` e `learn_query_results`
- persistência auditável por `proposal_id` e janela temporal
- cenários negativos e de governação cobertos em testes
- validação local verde com `pytest -q`, `ruff check src tests` e `mypy src tests`

### Retoma rápida
- estado operacional detalhado: ver `docs/plans/ODIN-F7-HANDOFF.md`
- data de referência do último corte documental: `2026-04-28`
- o roadmap e o test plan atuais não definem uma F8 formal
- backlog pós-F7 já decidido: ver `docs/plans/ODIN-POST-F7-BACKLOG.md` (referência 2026-04-28)

---

## 13. Notas finais

O Odin foi pensado para ser um sistema disciplinado, não um conjunto de scripts rápidos.  
Isso implica aceitar desde o início:

- mais estrutura
- mais governação
- mais validação
- menos improviso

É exatamente isso que vai impedir o projeto de se tornar frágil quando começar a tocar estado crítico, execução e dinheiro real.

---

## 14. Resumo executivo

Se tiveres de explicar o projeto em poucas linhas:

> O Odin é um sistema modular com CORE, MARKET, DECISION, RISK, EXEC, DASH, RECOVERY e LEARN, desenhado para operar com estado global coerente, validação forte, execução controlada, recovery seguro e evolução disciplinada.
