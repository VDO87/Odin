# CHANGELOG

## Unreleased - 2026-04-28

- Session handoff de fim de sessão consolidado em `docs/runbooks/ODIN-SESSION-HANDOFF.md`
- Operator Console validada ligada ao runtime demo em sandbox isolado (`$HOME/odin-runtime`)
- `inject-demo-quote-to-market` validado com atualização de MARKET runtime (`EURUSD`/`primary`)
- DECISION v1 scenario pack revalidado (safe/test/market stale/risk block)
- reinstalação limpa de sandbox e validação e2e documentadas
- reforço do fluxo de instalação isolada: sandbox em `$HOME/odin-runtime` tratado como descartável e repositório principal como única fonte de verdade
- runbooks atualizados para reset/reinstalação limpa com `scripts/odin_purge.sh` (`--dry-run`, `--remove-config`, `--remove-install`) e uso preferencial de `start_operator_console.sh` para testes de consola
- documentação da consola alinhada com endpoints atuais (`/api/config`, `POST /api/external/inject-demo-quote-to-market`, `POST /api/test/run-decision-cycle`) e caminhos de logs/estado em `$HOME/odin-runtime/runtime/...`
- validação técnica local reexecutada em 2026-04-28: `pytest -q` (`133 passed`), `ruff check src tests` (`All checks passed`), `mypy src tests` (`Success: no issues found in 84 source files`)
- fecho formal do corte principal F7 documentado com handoff operacional em `docs/plans/ODIN-F7-HANDOFF.md`
- matriz de rastreabilidade atualizada para refletir `REQ-LEARN-001..003` e reforço de governação em `REQ-DASH-002` como `TESTED`
- validação local de retoma executada em 2026-04-28: `pytest -q` (`75 passed`) e `ruff check src tests` (`All checks passed`)
- documentação técnica de F7 consolidada em `README.md`, `SDS-600`, `SDS-800` e `ODIN-TEST-PLAN`
- backlog pós-F7 formalizado em `docs/plans/ODIN-POST-F7-BACKLOG.md` com sequência `BF7-01..BF7-05`
- `DASH` passou a suportar query histórica explícita de LEARN (`LEARN_QUERY_HISTORY`) com filtros opcionais por `proposal_id` e janela temporal (`start_at_utc`/`end_at_utc`)
- refactor estrutural do módulo `DASH`: extração de modelos (`dash/models.py`), resolução de disponibilidade (`dash/availability.py`) e alarmística (`dash/alarms.py`), mantendo comportamento funcional
- refactor de persistência SQLite com helper interno `_list_records(...)` para reduzir duplicação nas listagens auditáveis
- reason-codes de rejeição LEARN consolidados em constantes no `DASH` para evitar strings dispersas e deriva semântica
- refactor do dispatch LEARN no `DASH` com handlers por ação e router interno, reduzindo complexidade ciclomática sem alterar contratos
- `project_state` no `DASH` simplificado com builders internos dedicados (availability permissionada, flags/health, modelos e recovery panel) para reduzir acoplamento
- `dispatch` geral do `DASH` refatorado com validações e handlers dedicados (`START`, `EXPORT_LOGS`, event-dispatch), mantendo os mesmos reason-codes e payloads
- contratos partilhados modularizados por domínio em `shared/contracts_parts` (`core`, `decision_exec`, `recovery`, `learn`) com `shared/contracts.py` mantido como camada de compatibilidade por re-export
- handoff de F7 atualizado para baseline de 2026-04-28 com validação completa (`pytest`, `ruff`, `mypy`) e decisão explícita de fecho/estabilidade
- `BF7-01` concluído: guards de transição formalizados com precedência explícita de bloqueios, vetor completo de bloqueios no estado interno do CORE e cobertura adicional de precedência `kill/manual/recovery` em unit/integration
- `BF7-02` concluído: núcleo RISK+EXEC endurecido com reason-codes críticos estáveis e evidência persistida de expiração, slippage, divergência e idempotência no execution ledger
- especificação inicial da `INTELLIGENCE LAYER` adicionada (`SDS-900`) com boundaries advisory, contratos (`advisory_request/response/snapshot`) e gating por profile (`lite/standard/full`)

- perfis de execução `lite`, `standard` e `full` introduzidos, com `lite` por defeito
- `DASH-lite` operacional introduzido, sem surface LEARN em `lite`
- execution ledger auditável persistido em SQLite
- schema versioning e migrations explícitas em `SQLiteStateStore`
- `INSTALL_ODIN.sh` endurecido com `--profile`, `--dry-run` e validação de config
- documentação e testes atualizados para o corte de operação inicial em hardware limitado

## 0.1.0

- estrutura inicial do repositório criada
- documentação reorganizada em `docs/`
- `SDS-100-CORE.md` adicionado
- `ODIN-TEST-PLAN.md` adicionado
- `ODIN-ENGINEERING-RULES.md` adicionado
- modelo de memória auxiliar e integração opcional com MemPalace adicionados
- documentação de software necessário adicionada
- scripts de bootstrap e verificação de pré-requisitos adicionados
- instalador automático de Ubuntu Server adicionado
- primeira implementação executável do CORE adicionada com SQLite, state machine, startup, heartbeat e testes base
