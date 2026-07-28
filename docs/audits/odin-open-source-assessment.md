# ODIN/Hermes — Avaliacao tecnica e open source

**Data:** 2026-07-27  
**Escopo:** auditoria read-only do repositorio, runtime local e candidatos open
source. Nenhum pacote foi instalado e nenhuma capacidade financeira foi ativada.

## Conclusao executiva

ODIN e uma base Python local, pequena e deliberadamente *fail-closed*. Esta
pronto para continuar como plataforma de observacao e investigacao, mas **nao
e ainda um sistema de demo trading**: o adaptador MT5 e mock-only, todos os
dados de mercado existentes sao mock/CSV local e nao ha observador XTB.

O beneficio real imediato nao vem de instalar um motor quant ou um agente de
browser. Vem de fechar quatro lacunas com interfaces estreitas e testes:

1. reparar a regressao dos testes de seguranca causada pelo HTML do cockpit;
2. consolidar a politica documental MT5 (mock-only vs futura deteccao demo);
3. criar o contrato de fonte publica read-only com proveniencia e cache;
4. criar um observador XTB isolado, somente apos ADR e branch dedicada.

**Decisao de portfolio:** nao adoptar nenhum dos candidatos nesta fase. A
unica adocao futura proposta e **Playwright Python**, por tras de um servico
local de capacidades fixas para XTB, depois de aprovacao explicita. Tudo o
resto fica em laboratorio, referencia ou rejeitado por licenca, superficie de
ataque, custo operacional ou sobreposicao.

## Evidencia recolhida

| Item | Resultado |
| --- | --- |
| Git | `master`, limpo, sem remoto; tag `v0.1.0-local-safe-runtime` |
| Historico recente | `f6b63c9 Add fail-closed MT5 demo guard`; serie A14-A23 e cockpit local |
| Runtime | uma distro `Ubuntu-ODIN` WSL2, Ubuntu 26.04 LTS; parada fora de comandos auditados |
| Codigo/testes | 91 modulos Python em `src/odin`; 90 ficheiros de teste, 554 testes recolhidos |
| Dependencias | `pyproject.toml` declara Python >=3.11 e **nenhuma** dependencia runtime |
| Persistencia | SQLite e JSONL; dados/logs/runtime ignorados pelo Git; arquivo host em `D:\ODIN_LOCAL` |
| Modelo local | Ollama detectado em validacao anterior; M4000 8 GB reservada; na observacao atual GPU 41 C, 0 MiB, display desativado |
| MT5 | terminal Windows instalado e processo `terminal64.exe` observado; codigo ODIN continua `MOCK_ONLY` e nao tenta ligar |
| Portas | nao ha processo ODIN/dashboard persistente nem porta de aplicacao exposta durante a auditoria |

### Arquitetura atual

- **Core/Risk:** `core`, `risk`, `contracts` e `decision` constroem estados e
  gates observacionais. `safe_to_trade`, `real_trading` e
  `execution_allowed` sao falsos por desenho.
- **Adapters:** mercado e MT5 sao mocks; MT5 possui bridge, simbolos, feed e
  gates de qualidade mock. `demo_guard.py` aceita somente a configuracao
  textual `demo`, sem ligacao.
- **Dados/research:** importacao CSV Forex, cache por hash/proveniencia e
  gates de frescura/gaps; `historical_return` e o unico relatorio research.
- **Hermes:** sumarios, supervisor, skills, memoria SQLite/JSONL e adaptador
  Ollama localhost. A indisponibilidade do modelo degrada, nao desbloqueia.
- **Operacao:** dashboard HTTP local read-only, CLI, smoke de 21 modulos,
  relatorios operacionais e `scripts/validate_wsl.sh` com `ulimit`/timeouts.

## Resultado de validacao

O smoke passou: 21 modulos, estado bloqueante confirmado e todas as flags
financeiras falsas. A validacao completa demorou 386 s e falhou em **7
testes**. A causa foi confirmada: as guardas de nao-execucao varrem todo
`src/odin` e tratam a palavra `click` como proibida; o cockpit contem
`<button onclick="loadAll()">`.

Isto nao e automacao de browser nem XTB, mas e uma regressao real da suite:
enquanto existir, `scripts/validate_wsl.sh` falha. A correcao deve preservar
as guardas contra automacao e substituir o handler inline por um listener JS
ou limitar a busca das guardas a modulos com capacidade financeira. Fazer essa
alteracao requer branch e revisao separadas.

## Problemas e lacunas priorizados

| Prioridade | Lacuna ou risco | Impacto | Acao recomendada |
| --- | --- | --- | --- |
| P0 | 7 testes de guardas falham | validacao completa vermelha | corrigir o falso positivo sem enfraquecer a politica |
| P0 | `MT5_SHADOW_PLAN.md` proibe deteccao terminal, mas `ODIN_ALIVE_DEMO_PLAN.md` preve demo guard/deteccao futura | politica ambigua | ADR de fronteira MT5 demo; manter mock-only ate aprovado |
| P0 | nao ha threat model, runbook de emergencia, gestao de segredos ou ADRs nos caminhos pedidos | risco e operacao nao auditaveis | documentar antes de integrar browser/dados autenticados |
| P1 | nao ha fornecedor publico real, adaptador HTTP, cache de respostas, eventos de falha ou anti-injecao | observacao real indisponivel | contrato `public_data` read-only, HTTP allowlist e fixtures |
| P1 | XTB so tem plano manual, sem observador | sem comparacao/observacao XTB | prototipo Playwright isolado depois de ADR |
| P1 | MT5 nao tem deteccao, login demo, reconexao, reconciliacao ou kill switch | nao pronto para demo | nao implementar antes de dados/observabilidade e decisao de politica |
| P2 | dashboard e HTML unico com polling, sem metricas historicas | diagnostico limitado | evoluir depois de dados reais; manter read-only |
| P2 | sem lockfile, SBOM ou auditoria de dependencias | supply chain antes de primeira dependencia | adoptar `uv`/lockfile, hashes e `pip-audit` na primeira PR de deps |

## Matriz de decisao

Legenda: **Adoptar** = unico componente previsto para integracao futura;
**Laboratorio** = ambiente isolado, sem Hermes operacional nem credenciais;
**Referencia** = estudar design/API sem dependencia; **Rejeitar** = nao usar;
**Adiar** = reavaliar apenas quando a lacuna existir. Compatibilidade pressupoe
Windows+WSL2, Python >=3.11 e 16 GB RAM/Quadro M4000 8 GB.

| Projeto | Finalidade / compatibilidade | Licenca e risco principal | Decisao | Justificacao |
| --- | --- | --- | --- | --- |
| Playwright | browser deterministico, Python/Node, WSL/Windows | Apache-2.0; cookies/sessao | **ADOPTAR (futuro)** | menor camada para XTB; wrapper de allowlist, perfil dedicado e funcoes fixas |
| Playwright MCP | ferramentas browser para agentes | Apache-2.0; nao e fronteira de seguranca | **REFERENCIA** | desenvolvimento/Codex apenas, nunca exposto ao Hermes |
| PinchTab | CLI/ponte Go multi-browser | MIT; stealth, API local e capacidade generica | **REJEITAR** | sobrepoe Playwright e aumenta superficie |
| Vercel Agent Browser | CLI/daemon CDP para agentes | MIT; perfis/cookies e daemon persistente | **REJEITAR** | capacidade generica e risco de sessao excessivos |
| Chrome DevTools MCP | diagnostico de Chrome | Apache-2.0; controlo total e telemetria por defeito | **REFERENCIA** | desenvolvimento manual com opt-out; nunca servico ODIN |
| Crawlee | crawlers Node/HTTP/browser | Apache-2.0; Node/proxies/filas | **ADIAR** | APIs oficiais/HTTP Python bastam; reavaliar para fontes dinamicas permitidas |
| Browser Use | browser controlado por LLM | MIT; LLM/cloud/controlo generico | **REJEITAR** | viola o modelo de capacidades limitadas para XTB |
| Stagehand | browser agent com LLM | MIT; dependencia LLM e Browserbase | **REJEITAR** | sem valor face a Playwright restrito |
| Browserless | browser como servico Docker | SSPL/comercial | **REJEITAR** | licenca e infraestrutura desnecessaria |
| Steel Browser | sandbox/API browser Docker | Apache-2.0; servico REST e Docker | **ADIAR** | bom isolamento, mas pesado para 16 GB e inutil antes do prototipo simples |
| VectorBT | pesquisa vetorizada/heatmaps | Apache-2.0 + Commons Clause | **REJEITAR** | nao e open source permissivo; nao integrar no produto |
| NautilusTrader | motor event-driven deterministico | LGPL-3.0; Rust/Cython complexo | **REFERENCIA** | excelente modelo de execucao/reconciliacao, excessivo para substituir ODIN |
| QuantConnect LEAN | motor C#/Python de backtest | Apache-2.0; .NET/dados/adaptadores | **LABORATORIO** | validacao independente futura, nao componente do core |
| Microsoft Qlib | research/ML temporal | MIT; dados/ML pesados | **LABORATORIO** | so apos dataset versionado e validacao temporal |
| FinRL | RL financeiro | MIT; simulador/reward e instabilidade | **LABORATORIO** | educacional, nunca risco/execution; comparar com baselines |
| OpenBB | plataforma de dados financeiros | AGPL-3.0 | **REJEITAR** | copyleft forte, providers e superficie maiores que a necessidade |
| Riskfolio-Lib | CVaR/alocacao/risk parity | dependencias CVXPY pesadas | **LABORATORIO** | potencial para portfolio multiativo, nao necessario para Forex inicial |
| PyPortfolioOpt | alocacao classica | MIT; estimativas frageis | **LABORATORIO** | menor e auditavel, somente quando houver multiativo |
| FinGPT | modelos/datasets financeiros | MIT; modelos 6B-13B/cloud examples | **ADIAR** | M4000 8 GB e 16 GB RAM favorecem Ollama pequeno; nao ha necessidade provada |
| AIOMQL | wrapper async MT5 | MIT; bot/execution/config JSON de credenciais | **REJEITAR** | abstrai demasiado e conflita com guardas/idempotencia proprias |
| Backtesting.py | backtest simples | AGPL-3.0 | **REJEITAR** | licenca e limites intrabar conhecidos; nao adoptar |
| Backtrader | backtest event-driven legado | GPL-3.0; manutencao antiga | **REJEITAR** | copyleft e risco de manutencao |
| PyBroker | backtest/ML/walk-forward | licenca a confirmar; escopo ML amplo | **ADIAR** | reavaliar apenas se LEAN/QSTrader nao cobrirem validacao |
| QSTrader | backtest modular schedule-driven | MIT; suporte documentado ate Python 3.12 | **REFERENCIA** | boa separacao signal/portfolio/execution, incompatibilidade a validar no Python atual |

## Riscos de seguranca

1. **Segredos e sessao:** `.env` esta ignorado e o exemplo e seguro, mas nao
   existe validacao central, redacao estruturada, rotacao/retenção ou threat
   model.
2. **Browser/XTB:** qualquer MCP/CLI de browser generico permite navegacao,
   inputs e extracao de cookies. Hermes deve receber somente respostas
   estruturadas de funcoes allowlisted, nunca ferramentas click/type/JS.
3. **Supply chain:** sem deps hoje e um ponto forte; a primeira adicao precisa
   de lockfile, pin, hash, scan e revisao de licenca.
4. **MT5:** `terminal64.exe` existe e estava em execucao no host, mas o ODIN
   nao lhe fala. Antes de demo deve existir deteccao de tipo de conta,
   process isolation, kill switch, idempotencia e reconciliacao.
5. **WSL:** uma sessao Windows nao elevada nao lista a distro, enquanto o
   contexto elevado lista `Ubuntu-ODIN`. Scripts operacionais devem declarar
   explicitamente este requisito e nunca assumir que “sem distro” e estado
   verdadeiro.
6. **Prompt injection/dados:** uma futura recolha deve tratar texto remoto como
   dado nao confiavel, guardar hash/proveniencia e impedir que instrua Hermes.

## Arquitetura alvo minima

```text
APIs oficiais/HTTP -> PublicDataAdapter -> cache/proveniencia/gates -> Hermes read-only
XTB (perfil Chromium dedicado) -> XtbObserver Playwright allowlisted -> resumo redigido -> Hermes read-only
datasets versionados -> research lab (isolado) -> relatorio humano
ODIN core/risk/state/audit -> MT5 demo adapter futuro (guardado) -> MT5
```

Nao ha seta Hermes->browser generico, Hermes->MT5 ou dados autenticados->LLM
cloud. Risk e kill switch devem vencer qualquer fluxo futuro.

## Sequencia proposta e rollback

1. Branch `audit/fix-safety-guard-html`; corrigir a regressao P0 e executar
   validacao completa. **Rollback:** reverter um commit unico.
2. ADR-001 (browser) e ADR-005 (MT5), threat model e runbooks; sem deps.
3. Branch `feature/public-data-contract`; interfaces, fixtures, timeout,
   allowlist e testes de proveniencia. **Rollback:** nao ligar provider.
4. Branch `lab/xtb-observer-playwright`; perfil separado, localhost, token
   local, allowlist e testes negativos de ordem. **Rollback:** apagar perfil e
   desinstalar Playwright; nunca toca no core.
5. So apos reliability window, aprovar uma PR separada para deteccao MT5 demo
   read-only. Login e qualquer ordem continuam a exigir autorizacao humana.

## Fontes de decisao

- Playwright MCP declara explicitamente que nao e uma fronteira de seguranca:
  <https://github.com/microsoft/playwright-mcp>
- Crawlee (Apache-2.0) e adequado apenas quando HTTP direto nao bastar:
  <https://github.com/apify/crawlee>
- Chrome DevTools MCP expoe os dados do browser e recolhe estatisticas por
  defeito: <https://github.com/ChromeDevTools/chrome-devtools-mcp>
- VectorBT usa Apache-2.0 com Commons Clause, nao uma licenca permissiva pura:
  <https://github.com/polakowo/vectorbt>
- NautilusTrader e LGPL-3.0, Rust-native e event-driven:
  <https://github.com/nautechsystems/nautilus_trader>
- OpenBB e AGPL-3.0: <https://github.com/OpenBB-finance/OpenBB>
- AIOMQL expoe um framework de bots/execution e configuracao de credenciais:
  <https://github.com/Ichinga-Samuel/aiomql>
