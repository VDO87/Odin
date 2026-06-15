# Treasury Policy

O Treasury Engine governa dinheiro, capital disponivel, liquidez e enquadramento fiscal operacional.

Politicas:

- Treasury vence Hermes em materia de dinheiro.
- Alocacoes de capital exigem revisao humana.
- FIRE, ETFs e accoes em XTB ficam em modo manual/assistido.
- O sistema nao deve emitir aconselhamento fiscal definitivo.
- Validacao fiscal para Portugal deve ser tratada como requisito de revisao.

## A4 - Skeleton PT

O Treasury A4 e read-only/compute-only. Todos os valores arrancam a zero e `safe_to_transfer=false`.

Bloqueios por defeito:

- `treasury_skeleton_read_only`
- `no_real_broker_data`
- `tax_reserve_not_validated`
- `protected_capital_policy_not_funded`
