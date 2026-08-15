# ODIN — ESTADO CANÓNICO, ARQUITETURA E PLANO DE CONCLUSÃO

**Data de consolidação:** 2026-08-15  
**Objetivo deste ficheiro:** substituir a dispersão entre vários documentos e servir como **fonte única de verdade operacional** para o estado atual do ODIN, plano de conclusão da DEMO supervisionada e fronteira para a fase seguinte.

---

# 1. REGRA PRINCIPAL

O ODIN **não está autorizado para trading real nem para envio de ordens DEMO**.

As seguintes condições permanecem obrigatórias:

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

Também permanecem bloqueados:

- `MT5 order_send`;
- execução automática;
- trading real;
- depósitos;
- ordens DEMO;
- autonomia financeira da LLM;
- autonomia financeira do Hermes;
- qualquer bypass ao Risk Engine ou ao Command Bus.

O estado atual é:

> **ODIN DEMO / OBSERVAÇÃO LOCAL / SUPERVISIONADO**

A conclusão desta fase significa ter uma plataforma local robusta, reproduzível, auditável e pronta para testes supervisionados.

Não significa autorização para operar dinheiro.

---

# 2. OBJETIVO DO PRODUTO NESTA FASE

Entregar uma aplicação local de investimento e treino **DEMO supervisionada**, composta por:

- **TradeDesk** para o operador visualizar:
  - conta MT5 DEMO;
  - EURUSD;
  - posições;
  - histórico;
  - métricas;
  - replay;
  - estado de risco;
  - qualidade/frescura dos dados;

- **Cockpit técnico** em `/cockpit` para:
  - saúde do ODIN;
  - saúde do Hermes;
  - logs;
  - dados;
  - recursos;
  - guardrails;
  - estado dos serviços;

- **MT5 DEMO collector** exclusivamente em leitura;
- **dados públicos Forex/económicos** com proveniência;
- **Hermes local** apenas para diagnóstico, resumo e análise de evidência;
- **Replay** claramente identificado como simulação;
- **persistência local** em `D:\ODIN_LOCAL`;
- **nenhuma ordem financeira**.

---

# 3. ESTADO LOCAL ATUAL CONHECIDO

## 3.1 Ambiente

- WSL único: `Ubuntu-ODIN`;
- repositório local:
  - `/home/odin/projects/odin`
- branch de trabalho conhecida:
  - `audit/p0-safety-and-docs`
- checkpoint conhecido:
  - `5b20a3d test: extend redaction across operator surfaces`

> O Codex deve confirmar estes dados antes de cada nova fase.  
> Se o estado local divergir deste ficheiro, deve atualizar este documento com evidência.

## 3.2 Verificação operacional — 2026-08-15

Classificação da divergência anterior: `IMPLEMENTAÇÃO MAIS AVANÇADA`.

Evidência local: o ramo mantém-se `audit/p0-safety-and-docs`, mas o HEAD
encontrado era `0e210b3 security-event-secret-redaction`, e não o checkpoint
histórico `f15393e`. Os checkpoints desta execução são `b314264` (contrato e
importador P0), `71af19b` (apresentação P0 no TradeDesk) e `5b20a3d` (P1).

Foi confirmado também: `Ubuntu-ODIN` (WSL2), `D:\ODIN_LOCAL`, Ollama local com
`qwen2.5-coder:1.5b` e Quadro M4000 sem display (40 °C no momento da sonda).
MT5, TradeDesk, cockpit e Hermes têm implementação e testes locais; a sua
validação operacional final permanece requisito da acceptance baseline.

---

# 4. COMPONENTES JÁ ENTREGUES

## 4.1 TradeDesk

Já existe interface local de operador.

Funções já presentes ou demonstradas:

- visualização local;
- ligação ao estado do ODIN;
- integração com dados MT5 DEMO read-only;
- integração com replay;
- integração com informação operacional;
- lançador;
- atalhos no Ambiente de Trabalho.

Ainda necessita de acabamento e walkthrough final.

---

## 4.2 Cockpit técnico

Já existe cockpit local.

Objetivo:

- mostrar saúde;
- mostrar logs;
- mostrar Hermes;
- mostrar estado de dados;
- mostrar guardrails;
- permitir diagnóstico sem execução financeira.

Permanece **read-only**.

---

## 4.3 MT5 DEMO

Já foi testado em modo exclusivamente de leitura.

Dados conhecidos já lidos:

- conta DEMO;
- posições;
- EURUSD;
- tick EURUSD;
- candles M15.

Nenhuma ordem foi enviada.

O MT5 continua a ser fonte operacional DEMO.

---

## 4.4 Dados públicos ECB

Já existe integração com dados públicos ECB.

Inclui:

- timeout;
- cache;
- hash;
- proveniência;
- frescura;
- eventos de falha.

Dados externos são considerados conteúdo não confiável até passarem pelos respetivos controlos.

Não podem gerar execução financeira.

---

## 4.5 Hermes

Hermes está integrado como componente local.

Estado obrigatório:

```text
LOCAL_ONLY
NO_EXECUTION
NO_FINANCIAL_AUTHORITY
```

Funções permitidas:

- diagnóstico;
- resumo;
- explicação;
- análise de evidência sanitizada;
- identificação de falta de dados;
- correlação de informação;
- apoio técnico.

Funções proibidas:

- envio de ordens;
- alteração autónoma do Risk Engine;
- ativação de execução;
- gestão autónoma de credenciais;
- alteração de guardrails sem revisão.

---

## 4.6 Replay

Existe replay claramente identificado como simulação.

O replay deve permanecer sempre separado de:

- MT5 DEMO;
- dados públicos live;
- qualquer futura execução.

---

## 4.7 Persistência

Persistência local prevista e utilizada em:

```text
D:\ODIN_LOCAL
```

Inclui ou deve incluir:

- JSONL;
- SQLite;
- cache;
- relatórios;
- artefactos;
- dados sanitizados;
- resultados de replay.

Segredos não podem ser persistidos.

---

## 4.8 Shadow cycle

Já existe ciclo shadow factual.

Estado atual:

- confirma disponibilidade;
- confirma frescura;
- guarda evidência;
- não decide financeiramente;
- não executa.

---

## 4.9 Kill switch

O kill switch DEMO já está representado:

- na reconciliação;
- no resumo operacional;
- nos guardrails.

O kill switch deve continuar a ser independente de LLM.

---

# 5. TESTES CONHECIDOS

Última validação integral conhecida:

```text
597 testes + 3 subtestes aprovados
```

Este número é uma referência histórica.

O Codex deve:

- voltar a executar a suite no estado final;
- não assumir que estes testes continuam verdes;
- não remover testes para obter aprovação artificial;
- registar o número final real no relatório de aceitação.

---

## 5.1 Suite completa resolvida — 2026-08-15

Evidência final no checkpoint `2129610 fix: close SQLite connections after storage operations`:

```text
606 passed, 11 subtests passed in 7m22s
limite normal: 1024 descritores
```

A causa foi investigada antes de alterar limites: várias operações de `SQLiteStore`
usavam o context manager da ligação SQLite, que faz commit/rollback mas não fecha o
descritor. A correção passou a fechar sempre a ligação, com teste de ciclo de vida
de 256 escritas. Não foram removidos nem ignorados testes. O watchdog global usado
foi 900 segundos; os timeouts específicos mantêm-se como proteção contra hangs.

# 6. SEGURANÇA E GUARDRAILS PERMANENTES

## 6.1 Local-first

- serviços locais;
- localhost;
- sem cloud obrigatória;
- sem exposição de APIs internas para a Internet.

---

## 6.2 Fail-closed

Quando existe dúvida, erro, dados em falta ou inconsistência:

```text
BLOCK
UNKNOWN
INSUFFICIENT_DATA
STALE
UNAVAILABLE
```

Nunca assumir um valor válido apenas para manter o pipeline a funcionar.

---

## 6.3 Temperatura

Guardrail térmico:

```text
>= 80 °C → interromper carga
```

Aplicável a CPU/GPU conforme o monitor disponível.

---

## 6.4 WSL

- timeout em comandos;
- watchdog;
- recovery controlado;
- sem loops infinitos;
- sem daemon autónomo não autorizado.

---

## 6.5 GPU / LLM

- Quadro M4000 dedicada ao LLM local;
- no máximo um modelo Ollama ativo, salvo revisão futura;
- M4000 sem display;
- consumo de recursos monitorizado.

---

## 6.6 Git

Proibido:

```text
git reset --hard
git push --force
merge automático
```

Também:

- não apagar trabalho local sem backup;
- não enviar `.env`;
- não enviar credenciais;
- não enviar cookies;
- não enviar modelos;
- não enviar caches;
- não enviar logs pesados;
- não enviar dumps com dados sensíveis.

---

# 7. ESTADO DAS TAREFAS DE CONCLUSÃO

## P1.1 — REDACTION JSONL/SQLITE

**Estado comunicado pelo Codex: IMPLEMENTADO, confirmação parcial**

O Codex informou:

> redaction em JSONL/SQLite, com teste automático.

Este item deve ser considerado:

```text
IMPLEMENTADO — CONFIRMADO PARA JSONL/SQLITE; EXPANSÃO P1 PENDENTE
```

até ser novamente confirmado no acceptance test final.

O relatório final deve registar:

- ficheiro do teste;
- comando;
- resultado;
- commit.

---

# 8. P0 — PRIORIDADE ATUAL: HISTÓRICO DE CANDLES

**Estado em 2026-08-15:** o contrato v1 e importador fail-closed foram
implementados nos checkpoints `b314264` e `71af19b`, com `11 passed, 8
subtests passed` na validação P0/TradeDesk. A integração de apresentação no
TradeDesk está concluída. A validação end-to-end contra o destino real
`D:\ODIN_LOCAL` continua pendente porque não existe CSV canónico com licença e
proveniência verificáveis no host; P0 não pode ainda ser aceite.

Esta é a prioridade imediata.

## 8.1 Contrato CSV canónico

Campos mínimos:

```text
symbol
timeframe
timestamp_utc
open
high
low
close
volume
source
source_version
schema_version
provenance
license
hash
```

Pode incluir campos adicionais, desde que documentados e versionados.

---

## 8.2 Regras obrigatórias do importador

O importador deve ser **fail-closed**.

Deve rejeitar:

- schema inválido;
- timestamp inválido;
- timestamps não UTC;
- linhas fora de ordem;
- duplicados;
- gaps incompatíveis com as regras;
- OHLC impossível;
- `NaN`;
- `inf`;
- ficheiro sem origem;
- ficheiro sem proveniência;
- hash inválido;
- símbolo incompatível;
- timeframe incompatível.

Não deve corrigir silenciosamente erros.

---

## 8.3 Destino dos dados

Guardar apenas artefactos validados em:

```text
D:\ODIN_LOCAL\artifacts\market-data
```

Cada dataset deve possuir:

- hash;
- origem;
- período;
- schema;
- proveniência;
- qualidade;
- data de ingestão;
- estado de validação.

---

## 8.4 TradeDesk

O TradeDesk deve mostrar para o histórico:

- fonte;
- período;
- frescura;
- qualidade;
- hash ou referência;
- motivo de bloqueio quando inválido.

Nunca deve transformar qualidade de dados em recomendação financeira.

---

# 8.5 Tentativa Dukascopy — estado atual

Fonte aprovada: Dukascopy Historical Data Export, apenas para uso interno ODIN
em DEMO/replay e sem redistribuição. A verificação do exportador/backend confirmou
que EUR/USD anuncia `MINUTE`, `HOUR` e `DAY`; M15 não é nativo no contrato da
fonte. Foi criado o checkpoint `38f2464` com descodificação M1 oficial, agregação
M1→M15 UTC determinística de janelas completas, testes e importação obrigatória
via o importador fail-closed.

Configuração proposta e documentada: EUR/USD BID, UTC,
`[2025-07-01T00:00:00Z, 2025-08-01T00:00:00Z)`, origem do exportador
`https://widgets.dukascopy.com/en/historical-data-export`, backend
`https://jetta.dukascopy.com/v1` e referência aos termos oficiais. Nenhuma
credencial ou cookie foi guardado.

**P0 continua NOT READY:** durante a recolha o fornecedor respondeu `HTTP 429 Too
Many Requests` sem `Retry-After`. É classificado como bloqueio externo transitório
(`SOURCE_RATE_LIMITED`), não como erro do importador. A política de aquisição é
limitada a três tentativas, com `Retry-After` respeitado ou backoff conservador
30 s/60 s com jitter; termina sem retry infinito e sem persistir dataset parcial.

Foi preparado o fallback manual fail-closed: aceita apenas CSV M1 UTC do
**Dukascopy Historical Data Export**, valida cabeçalho, timezone, metadados de
origem, ordering e OHLCV, agrega deterministamente M1→M15 e aplica todo o contrato
P0. O manifesto aceite regista URL, data de aquisição, símbolo, período derivado,
timezone, formato, hash, proveniência e referência aos termos. Não existe ainda
dataset Dukascopy real aceite em `D:\ODIN_LOCAL\artifacts\market-data`; P2 não
inicia antes da aceitação integral P0.

# 8.6 Fonte P0 OANDA Practice — preparada, ainda bloqueada

Foi autorizada a preparação de OANDA v20 **Practice** exclusivamente como fonte
histórica read-only, sem autorização de trading. O adaptador fixo usa apenas
`GET /v3/accounts/{accountID}/instruments/EUR_USD/candles` no host oficial
`https://api-fxpractice.oanda.com`, com `EUR_USD`, `price=B`, `granularity=M1`,
UTC e o intervalo `[2025-07-01T00:00:00Z,2025-08-01T00:00:00Z)`.

O RAW JSON é imutável, paginado abaixo de 5.000 M1, recebe SHA-256 por página e
por lote, e só avança após validação de BID, UTC, período completo, gaps e OHLCV.
A agregação M1→M15 permanece a implementação determinística existente, e o
manifesto M15 referencia o hash/artefacto RAW. Não há endpoints de execução,
posição, transação ou configuração no adaptador; testes offline verificam esse
limite e a ausência de credenciais em erros/superfícies auditáveis.

**P0 continua NOT READY:** falta a conta Practice, o token pessoal local e a URL
do acordo de licença API aplicável à divisão da conta. Essa URL é obrigatória
para preencher `license` honestamente; sem ela o importador bloqueia e não reduz
o contrato canónico. O detalhe operacional está em `docs/OANDA_P0_READONLY.md`.

# 9. P1 — SEGURANÇA DE SEGREDOS

Embora P1.1 tenha sido reportado como concluído, a fase de segurança só fecha quando existir prova mais abrangente.

**Estado em 2026-08-15:** testes de sentinelas foram expandidos e aprovados no
checkpoint `5b20a3d`: JSONL, SQLite, relatório, HTML TradeDesk/cockpit, API
localhost, diagnósticos Hermes e stdout de teste não expõem os valores. A
documentação de rotação, emergência, kill switch e recuperação está em
`docs/SECRET_HANDLING_AND_RECOVERY.md`.

**Suite completa:** resolvida conforme a secção 5.1; não é bloqueio de P3.

## 9.1 Redaction tests

Criar valores-sentinela de teste e confirmar que não aparecem em:

- JSONL;
- SQLite;
- logs;
- stdout/stderr;
- exceptions;
- relatórios;
- HTML;
- respostas de API localhost;
- snapshots;
- eventos;
- respostas Hermes;
- diagnósticos.

Nunca imprimir os segredos reais.

---

## 9.2 Documentação

Documentar:

- rotação de credenciais;
- localização dos segredos;
- emergência;
- kill switch;
- recuperação;
- revogação.

---

# 10. P2 — TRADEDESK FINAL

O TradeDesk deve separar claramente três domínios.

---

## 10.1 MT5 DEMO

Mostrar, quando tecnicamente disponível:

- estado da ligação;
- identificação clara `MT5 DEMO`;
- balance;
- equity;
- P&L;
- drawdown;
- posições;
- histórico fechado;
- EURUSD;
- timestamp;
- freshness;
- reconciliação.

Nunca mostrar uma conta DEMO como conta real.

---

## 10.2 REPLAY

Mostrar sempre como:

```text
SIMULAÇÃO / REPLAY
```

Campos recomendados:

- dataset;
- hash;
- período;
- capital virtual;
- trades simulados;
- P&L simulado;
- drawdown;
- win rate;
- expectancy;
- profit factor;
- Sharpe;
- Sortino;
- spread assumido;
- slippage;
- custos.

Sharpe/Sortino só devem ser apresentados quando matematicamente válidos.

---

## 10.3 DADOS PÚBLICOS / INTELLIGENCE

Mostrar:

- fonte;
- data;
- timestamp;
- frescura;
- proveniência;
- qualidade;
- estado.

Futuramente poderá incluir:

- macro;
- notícias;
- contexto;
- sentimento.

Mas não deve apresentar opinião de uma LLM como dado factual.

---

# 11. P3 — ENTREGA DEMO SUPERVISIONADA

## 11.1 Testes finais desta baseline

Executar:

- suite completa;
- smoke tests;
- testes de integração;
- testes de redaction;
- testes fail-closed;
- testes do importador;
- testes do TradeDesk;
- testes do cockpit;
- testes dos atalhos;
- testes do launcher;
- testes de persistência;
- testes MT5 read-only.

Também executar:

```text
ruff
mypy direcionado
git diff --check
```

---

## 11.2 Walkthrough do operador

Criar:

```text
docs/OPERATOR_WALKTHROUGH.md
```

O walkthrough deve validar, após reboot quando aplicável:

1. iniciar Windows;
2. iniciar WSL;
3. iniciar componentes necessários;
4. abrir TradeDesk pelo atalho;
5. abrir `/cockpit`;
6. verificar ODIN;
7. verificar MT5;
8. verificar Hermes;
9. verificar Ollama;
10. verificar market data;
11. executar refresh controlado;
12. executar replay;
13. consultar relatório;
14. parar ODIN corretamente.

---

## 11.3 Processo persistente

Não criar automaticamente.

Pode apenas ser preparado depois de:

- baseline concluída;
- testes verdes;
- autorização explícita do operador.

Quando autorizado, deve ter:

- watchdog;
- kill switch;
- logs;
- recovery;
- controlo térmico;
- stop manual claro.

---

# 12. DEFINITION OF DONE — BASELINE DEMO

A fase atual só pode ser declarada concluída quando TODOS os seguintes pontos forem verdadeiros:

- suite completa verde;
- histórico CSV validado;
- importador fail-closed validado;
- artefactos persistidos no D:;
- redaction validada;
- TradeDesk validado;
- cockpit validado;
- atalhos validados;
- launcher validado;
- MT5 DEMO read-only validado;
- dados MT5 frescos;
- reconciliação validada;
- ECB/dados públicos com proveniência;
- replay claramente separado;
- Hermes validado em modo local e sem execução;
- kill switch validado;
- guardrails validados;
- walkthrough concluído;
- `git diff --check` limpo;
- relatório final criado.

Quando todos forem cumpridos:

```text
ODIN DEMO BASELINE
READY FOR SUPERVISED TESTING
```

Se faltar qualquer requisito crítico:

```text
NOT READY
```

e listar bloqueios.

---

# 13. RELATÓRIO FINAL OBRIGATÓRIO

Criar:

```text
docs/ODIN_DEMO_BASELINE_ACCEPTANCE_REPORT.md
```

O relatório deve conter:

- data;
- commit;
- branch;
- arquitetura;
- componentes;
- testes;
- número final de testes;
- resultados;
- datasets;
- estado MT5;
- estado Hermes;
- estado TradeDesk;
- estado cockpit;
- estado dos guardrails;
- redaction;
- limitações;
- riscos residuais;
- evidências;
- Definition of Done;
- instruções de arranque;
- instruções de paragem.

---

# 14. APÓS A BASELINE: CONGELAR

Quando P0 + P1 + P2 + P3 estiverem concluídos e aceites:

criar um checkpoint/tag/release de referência.

Nome conceptual:

```text
ODIN DEMO OBSERVATION BASELINE
```

A partir daí:

- não misturar novas experiências na baseline;
- alterações futuras devem ser feitas em branches dedicadas;
- cada novo componente deve ser comparado contra a baseline.

---

# 15. FASE SEGUINTE — ODIN SHADOW INTELLIGENCE

Esta fase **não faz parte da conclusão imediata P0-P3**.

Só começa após a baseline estar estável.

Objetivo:

> testar o cérebro completo do ODIN sem permitir qualquer ordem.

---

## 15.1 Pipeline alvo

```text
MT5 DEMO READ-ONLY
        ↓
Market Data Quality
        ↓
Historical + Live Context
        ↓
Macro / News / Intelligence
        ↓
Strategies
        ↓
ATLAS / Hermes
        ↓
Deterministic Risk Engine
        ↓
Decision Packet
        ↓
SHADOW SIGNAL
        ↓
EXECUTION BLOCKED
        ↓
Replay / Evaluation / Audit
```

---

## 15.2 Shadow signals

Podem existir apenas como proposta simulada:

```text
BUY
SELL
HOLD
NO_TRADE
BLOCKED
```

Campos mínimos:

```text
symbol
timestamp
timeframe
strategy_id
signal
confidence
reason_codes
evidence_refs
entry_reference
stop_reference
target_reference
expected_risk
data_quality
expiry
risk_decision
execution_allowed=false
```

Nenhum sinal pode chamar `order_send`.

---

## 15.3 Risk Engine

O Risk Engine deve permanecer determinístico.

Estados futuros possíveis em shadow:

```text
ALLOW_SHADOW
RESTRICT
BLOCK
KILL
```

Mesmo:

```text
ALLOW_SHADOW
```

significa:

```text
execution_allowed=false
```

---

# 16. FERRAMENTAS E SKILLS — SÓ DEPOIS DA BASELINE

Não instalar agora por impulso.

Candidatos já estudados:

- `Oh My Hermes`;
- `PinchTab`;
- `watchers`;
- `stocks`;
- `osint-investigation`;
- `De-Fluff`;
- `Codebase Memory MCP`;
- `Loop Library`;
- `YouTube Full`;
- skills macro/notícias próprias;
- OpenBB;
- VectorBT;
- MLflow;
- outras ferramentas de investigação.

---

## 16.1 Ordem futura recomendada

Após congelar a baseline:

1. Codebase Memory / compreensão do repositório;
2. Oh My Hermes / workflow routing;
3. Watchers;
4. browser isolado;
5. notícias e macro;
6. qualidade de dados;
7. estratégias shadow;
8. Risk Engine;
9. decision packets;
10. replay e benchmark;
11. soak tests;
12. apenas muito mais tarde considerar execução DEMO.

---

# 17. SKILLS PRÓPRIAS PRIORITÁRIAS PARA O FUTURO

Não implementar antes da baseline sem necessidade concreta.

Lista prevista:

```text
odin-project-state
odin-codebase-reconciliation
market-data-quality-gate
mt5-shadow-reconciliation
risk-policy-evaluation
decision-packet-builder
macro-release-ingestion
news-evidence-packet
strategy-replay-validation
bounded-research-loop
geopolitical-event-map
economic-vintage-control
post-trade-review
drawdown-and-kill-watch
safe-codex-handoff
```

---

# 18. O QUE NÃO FAZER AGORA

Até a baseline estar pronta:

- não adicionar auto-trading;
- não ativar ordens DEMO;
- não ativar ordens reais;
- não ativar `order_send`;
- não instalar dezenas de agentes;
- não introduzir SkillClaw no núcleo;
- não dar browser autenticado na XTB ao Hermes;
- não dar cookies pessoais;
- não criar dependências cloud obrigatórias;
- não reescrever toda a arquitetura sem necessidade;
- não iniciar RL;
- não aumentar indefinidamente o escopo;
- não transformar a conclusão numa investigação de frameworks.

Primeiro:

```text
TERMINAR
TESTAR
CONGELAR
```

Depois:

```text
EVOLUIR
```

---

# 19. INSTRUÇÃO CURTA PARA O CODEX

A instrução operacional atual é:

> Continua a conclusão do ODIN pela ordem P0 → P1 restante → P2 → P3.  
> Não expandir o escopo para novos agentes, novas frameworks, Shadow Intelligence ou execução.  
> Mantém todos os guardrails.  
> No final de cada fase executa testes, guarda evidência, cria checkpoint e atualiza este documento.  
> Quando todos os critérios da Definition of Done estiverem cumpridos, cria o `ODIN_DEMO_BASELINE_ACCEPTANCE_REPORT.md`.  
> Só depois de revisão e autorização explícita será iniciada a fase `ODIN SHADOW INTELLIGENCE`.

---

# 20. ESTADO ATUAL RESUMIDO

```text
ODIN
│
├── Infraestrutura local ................. OPERACIONAL
├── Ubuntu-ODIN .......................... OPERACIONAL
├── TradeDesk ............................ IMPLEMENTADO / A REFINAR
├── Cockpit .............................. IMPLEMENTADO
├── MT5 DEMO read-only ................... TESTADO
├── EURUSD / candles M15 ................. TESTADO
├── ECB public data ...................... IMPLEMENTADO
├── Proveniência/cache/hash .............. IMPLEMENTADO
├── Hermes local diagnóstico ............. IMPLEMENTADO
├── Replay ............................... IMPLEMENTADO / A VALIDAR
├── Shadow factual cycle ................. IMPLEMENTADO
├── Kill switch representation ........... IMPLEMENTADO
├── Redaction JSONL/SQLite ............... REPORTADO COMO CONCLUÍDO
├── CSV histórico canónico ............... EM CURSO / P0
├── Importador fail-closed ............... EM CURSO / P0
├── TradeDesk final ...................... P2
├── Operator walkthrough ................. P3
├── Processo persistente ................. NÃO AUTORIZADO
├── Shadow Intelligence .................. FASE FUTURA
├── Ordens DEMO .......................... BLOQUEADAS
└── Trading real ......................... BLOQUEADO
```

---

# 21. FONTES CONSOLIDADAS

Este documento consolida e substitui, para efeitos de planeamento, os conteúdos de:

- `00_LEIA_ME.md`
- `01_TIPOLOGIA_E_ARQUITETURA.md`
- `02_ESTADO_ATUAL.md`
- `03_PLANO_DE_CONCLUSAO.md`
- `04_PEDIDO_PARA_CHATGPT.md`

E incorpora as decisões mais recentes:

- P1.1 redaction comunicado pelo Codex como concluído;
- P0 definido como prioridade atual;
- P2 e P3 fecham a baseline;
- Shadow Intelligence é uma fase separada e posterior;
- novas skills/agentes/frameworks ficam fora do escopo até a baseline estar congelada.

---

# 22. PRINCÍPIO FINAL

O objetivo não é criar o maior sistema possível.

O objetivo é criar um sistema:

```text
FUNCIONAL
REPRODUZÍVEL
AUDITÁVEL
FAIL-CLOSED
SUPERVISIONADO
```

e só depois aumentar a autonomia de forma controlada.

**Primeiro terminar a máquina. Depois ensinar a máquina a pensar melhor.**
