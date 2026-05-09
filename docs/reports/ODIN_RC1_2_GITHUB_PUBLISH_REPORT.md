# ODIN RC1.2 GitHub Publish Report

## Data/Hora
- 2026-05-09 (Europe/Lisbon)

## Estado local confirmado
- Diretório: `/home/vdo/Secretária/Projects_Codex/Odin_Teste`
- Branch atual: `master`
- Working tree: limpa
- Commit RC1.2: `b074fae`
- Tags locais:
  - `v0.1.0-rc1-foundation`
  - `v0.1.1-rc1-runtime-hardening`
  - `v0.1.2-rc1-mt5-shadow`

## Remote configurado
- `origin https://github.com/VDO87/Odin.git` (fetch/push)

## Fetch e comparação
- `git fetch origin`: concluído com sucesso.
- Branches remotas listadas (`git branch -a`), incluindo `origin/main`.
- Histórico comparado com `git log --oneline --graph --decorate --all -n 40`.

## Publicação da branch
- Comando: `git push -u origin master:odin-rc1-local`
- Resultado: **não publicada** (falha de autenticação HTTPS).

## Publicação das tags
- `git push origin v0.1.0-rc1-foundation` -> **não publicada** (auth).
- `git push origin v0.1.1-rc1-runtime-hardening` -> **não publicada** (auth).
- `git push origin v0.1.2-rc1-mt5-shadow` -> **não publicada** (auth).

## Erro de autenticação
- Mensagem:
  - `fatal: could not read Username for 'https://github.com': No such device or address`
- Sem token impresso.
- Sem token guardado em ficheiro.
- Sem credenciais expostas.

## Próximos passos
1. Executar `gh auth login` e autenticar por browser (recomendado).
2. Repetir os pushes:
   - `git push -u origin master:odin-rc1-local`
   - `git push origin v0.1.0-rc1-foundation`
   - `git push origin v0.1.1-rc1-runtime-hardening`
   - `git push origin v0.1.2-rc1-mt5-shadow`

## Confirmação de proteção da main
- `main` não foi alterada.
- Não foi feito `force push`.
- Não foram apagadas branches.
