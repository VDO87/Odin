# ODIN GitHub Branch Strategy

## Branches principais
- `release/rc1`: branch principal atual do ODIN RC1.
- `archive/legacy-main-before-rc1`: arquivo da main antiga preservada.
- `main`: legado; não usar para desenvolvimento novo enquanto não houver consolidação formal.

## Tags de release
- `v0.1.0-rc1-foundation`
- `v0.1.1-rc1-runtime-hardening`
- `v0.1.2-rc1-mt5-shadow`

## Branches temporárias
- `codex/*`: branches temporárias sujeitas a auditoria.

## Regras operacionais
- Não usar `force push`.
- Não mover nem apagar tags de release RC1.
- Novas funcionalidades: `feature/<nome>`.
- Correcções: `fix/<nome>`.
- Investigação: `research/<nome>`.
