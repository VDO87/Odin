# A21 - Strategy Context Snapshot Mock

## Estado de prontidao

- Repositorio valido: `/home/odin/projects/odin`.
- Base funcional confirmada: `6256ed9 feat: implement A20 observation frame quality gate`.
- Infraestrutura Hermes/Ollama isolada no checkpoint local `c0b0a66`.
- Worktree dedicada: `/home/odin/worktrees/a21-strategy-context-snapshot`.
- Branch dedicada: `a21/strategy-context-snapshot`.
- A20 concluida e coberta por contratos, runtime, CLI, dashboard e testes de bloqueio.
- Nao foi encontrada implementacao anterior da A21.
- Suite anterior a esta preparacao: 499 testes aprovados.

## Objectivo

Criar um snapshot mock, imutavel e deterministico do contexto que uma estrategia poderia observar no futuro. O snapshot agrega apenas campos aprovados do frame A19 e do relatorio de qualidade A20.

A A21 nao interpreta o mercado, nao produz sinais, nao escolhe direccao, nao cria proposta e nao desbloqueia risco ou execucao.

## Contrato proposto

Nome do contrato: `StrategyContextSnapshot`.

Campos observacionais previstos:

- `component="strategy_context_snapshot"`;
- `status="OK"` apenas quando a entrada A20 e coerente;
- `snapshot_mode="MOCK_OBSERVATION_ONLY"`;
- `snapshot_version="A21.v1"`;
- `selected_source`;
- `primary_symbol`;
- `feed_quality_status`;
- `data_quality_status`;
- `frame_quality_status`;
- `strategy_status`;
- `decision_intent_status`;
- `risk_status`;
- `shadow_proposal_status`;
- `quality_gates_count`;
- `quality_gates_passed`;
- `context_fingerprint`, calculado deterministicamente apenas sobre campos observacionais aprovados;
- `safe_to_use_for_decision=false`;
- `decision_generated=false`;
- `trade_proposal_generated=false`;
- `risk_approved=false`;
- `execution_allowed=false`;
- `safe_to_trade=false`;
- `real_trading=false`;
- `reason`;
- `blockers`;
- `notes`.

O contrato deve usar `@dataclass(frozen=True)` e serializacao deterministica. Nao deve conter timestamps de relogio, UUID aleatorio, precos operacionais, direccao, tamanho de posicao ou parametros de ordem no fingerprint.

## Fontes permitidas

- `observation_frame_quality_status()` da A20.
- Campos observacionais do frame A19 ja expostos pela A20.
- Configuracao mock declarativa, caso estritamente necessaria.

Nao sao permitidas chamadas directas a broker, terminal MT5, rede, ficheiros de credenciais ou LLM durante a construcao do snapshot.

## Ficheiros provaveis

- `src/odin/contracts/strategy_context_snapshot.py` - contrato imutavel.
- `src/odin/decision/strategy_context_snapshot.py` - builder mock e fingerprint.
- `src/odin/contracts/events.py` - eventos de pedido, construcao e bloqueios.
- `src/odin/cli.py` - comando `strategy-context-snapshot`.
- `src/odin/dashboard/routes.py` - endpoint read-only `/strategy/context/snapshot`.
- `src/odin/dashboard/schemas.py` - schema documental do endpoint.
- `src/odin/core/smoke.py` - modulo seguro numero 18.
- `tests/test_a21_strategy_context_snapshot.py`.
- `tests/test_a21_strategy_context_snapshot_contracts.py`.
- `tests/test_a21_strategy_context_snapshot_cli_dashboard.py`.
- `tests/test_a21_strategy_context_snapshot_guards.py`.
- `README.md`, `CHANGELOG.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE_LOCK.md`, `docs/DASHBOARD_SPEC.md` e runbook local.

## Criterios de aceitacao

1. Duas entradas A20 semanticamente iguais produzem serializacao e fingerprint identicos.
2. O contrato e imutavel.
3. O snapshot copia somente campos autorizados.
4. Entrada A20 invalida produz estado bloqueado e explicavel.
5. Todos os flags criticos permanecem `false`.
6. O snapshot nunca e classificado como seguro para decisao.
7. Nao existem sinais BUY/SELL, direccao, entry, stop loss, take profit ou position sizing.
8. Nao existem imports ou chamadas reais MT5/XTB.
9. CLI devolve JSON deterministico e read-only.
10. Dashboard devolve o mesmo contrato sem capacidades de escrita.
11. Smoke inclui 18 modulos e continua bloqueante.
12. Testes A0-A20 continuam aprovados.
13. Ruff e mypy nao introduzem novos erros nos ficheiros A21.
14. `git diff --check` fica limpo.

## Divisao do trabalho

### Codex

- Fechar contrato e invariantes.
- Rever fingerprint e serializacao deterministica.
- Rever integracao CLI, dashboard e smoke.
- Validar guardas de seguranca e resultado final.

### Hermes

- Guardar estado da tarefa e checkpoints.
- Executar apenas validadores autorizados.
- Medir progresso e detectar repeticao de erros.
- Preparar escalamento compacto quando necessario.

### LLM local

- Propor boilerplate do contrato e testes numa sandbox.
- Corrigir erros simples dentro dos caminhos autorizados.
- Nao aplicar codigo directamente ao repositorio A21.
- Nao executar Git nem alterar politicas, risco ou trading.

## Pontos de revisao Codex obrigatoria

- Definicao final dos campos do contrato.
- Algoritmo e campos do fingerprint.
- Qualquer alteracao em `events.py`, CLI, dashboard ou smoke.
- Qualquer referencia a decisao, risco, proposta ou execucao.
- Diff final antes de commit.

## Riscos tecnicos

- Incluir campos volateis e perder determinismo.
- Confundir qualidade `OK` com autorizacao de decisao.
- Duplicar ou divergir dos contratos A19/A20.
- Aumentar `modules_count` sem actualizar testes historicos.
- Permitir ao modelo local alterar ficheiros fora do ambito.

Risco global estimado: medio, devido a integracao transversal; risco financeiro: baixo enquanto todos os bloqueios permanecerem imutaveis.

## Estrategia de rollback

1. Trabalhar apenas na worktree e branch A21.
2. Criar checkpoints locais somente depois de testes aprovados.
3. Nao fazer merge ou push automaticamente.
4. Se o diff sair do ambito, parar e escalar para revisao.
5. Em caso de falha, preservar logs e estado Hermes e abandonar apenas a branch/worktree A21 mediante aprovacao humana.
6. `master` permanece em `6256ed9` ate revisao e integracao expressas.

## Condicao para iniciar implementacao

A implementacao da A21 so pode comecar depois de aprovacao humana deste plano. A Fase 7 termina com a worktree preparada e este documento; nenhum modulo funcional A21 e criado nesta fase.
