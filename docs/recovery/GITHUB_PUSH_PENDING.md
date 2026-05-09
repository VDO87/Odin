# GitHub Push Pending (ODIN RC1.2)

## Estado
- Remote configurado: `origin=https://github.com/VDO87/Odin.git`
- Branch local pronta: `master` (HEAD `b074fae`)
- Tags locais prontas:
  - `v0.1.0-rc1-foundation`
  - `v0.1.1-rc1-runtime-hardening`
  - `v0.1.2-rc1-mt5-shadow`
- Push pendente por autenticação HTTPS.

## Erro encontrado
`fatal: could not read Username for 'https://github.com': No such device or address`

## Como autenticar sem expor credenciais
1. Usar GitHub CLI (recomendado):
   - `gh auth login`
   - escolher `GitHub.com`
   - `HTTPS`
   - autenticar por browser.
2. Alternativa com PAT:
   - criar PAT no GitHub com escopo `repo`;
   - usar apenas no prompt do Git quando pedido;
   - não guardar token em ficheiros do projeto.

## Comandos para concluir (sem force, sem tocar main)
```bash
git push -u origin master:odin-rc1-local
git push origin v0.1.0-rc1-foundation
git push origin v0.1.1-rc1-runtime-hardening
git push origin v0.1.2-rc1-mt5-shadow
```

## Segurança
- Não usar `--force`.
- Não apagar branches.
- Não fazer push para `main`.
- Não versionar `.env` real, segredos ou logs sensíveis.
