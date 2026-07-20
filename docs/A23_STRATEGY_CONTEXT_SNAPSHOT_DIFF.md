# A23 — Diff observacional de Strategy Context Snapshots

## Objetivo

A23 compara dois snapshots A21 fornecidos em memória. O resultado é
determinístico, read-only e não cria histórico, persistência adicional,
chamadas externas, decisão, proposta, aprovação de risco ou execução.

## Interfaces

- CLI: `python3 -m odin.cli strategy-context-snapshot-diff --before-json '<json>' --after-json '<json>'`
- Dashboard: `GET /strategy/context/snapshot/diff`
- Python: `strategy_context_snapshot_diff_status(before_snapshot=..., after_snapshot=...)`

O endpoint constrói duas cópias equivalentes do snapshot mock corrente; a
interface Python e CLI existem para comparar snapshots fornecidos pelo
operador, sem ler ficheiros externos.

## Regras fail-closed

- Ambos os snapshots têm de passar a qualidade A22.
- Os campos críticos de decisão, proposta, risco e execução têm de ser
  estritamente `false`.
- Campos em falta, fingerprints inválidas ou flags críticas ativas devolvem
  `status="BLOCKED"`; os flags de saída continuam todos a `false`.
- Apenas a whitelist A21 é comparada; alterações são ordenadas e descritivas,
  sem interpretação financeira.

## Validação

Executar o teste A23, CLI e smoke com um watchdog externo. Na distro
recuperada, usar `ulimit -n 8192` antes de suites longas.
