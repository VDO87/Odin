# Ensaio Controlado Hermes, Ollama e Codex

## Objectivo

A Fase 6 valida o fluxo completo numa sandbox descartavel, sem tocar no codigo critico do Odin e sem chamar automaticamente o Codex.

## Fluxo

1. Hermes cria e guarda o estado da tarefa.
2. O trabalhador local devolve apenas uma proposta JSON com ficheiros.
3. Os caminhos sao validados contra a lista autorizada.
4. A proposta e aplicada exclusivamente na sandbox da tarefa.
5. Hermes executa apenas `pytest`, Ruff e mypy nessa sandbox.
6. O motor mede progresso com resultados objectivos.
7. Uma correcao local delimitada e permitida quando existe possibilidade de progresso.
8. Falha repetida cria um pacote compacto para revisao Codex.
9. Uma implementacao aprovada pelos validadores fica em `AWAITING_APPROVAL`; nunca em `COMPLETED` automaticamente.

## Isolamento

- Raiz das sandboxes: `/home/odin/hermes_state/sandboxes`.
- Caminhos absolutos, `..`, symlinks e ficheiros fora do ambito sao recusados.
- O formato do trabalhador local aceita apenas a chave `files`.
- Nao sao aceites comandos produzidos pelo modelo.
- O validador tem uma lista fixa de tres comandos e timeout de 60 segundos.
- O pacote Codex e guardado em disco com `automatic_call=false`.
- Nao existe commit, push, merge, checkout, trading ou acesso a credenciais.

## Criterio de sucesso

O ensaio termina em `AWAITING_APPROVAL` quando pytest, Ruff e mypy passam. Uma falha repetida termina em `CODEX_REVIEW` e aguarda revisao manual. Ambos os resultados sao seguros e persistentes.

## Resultado do ensaio PHASE6-LIVE-01

O trabalhador local criou uma implementacao correcta de `is_even`, mas repetiu um teste sem importar a funcao. Pytest e Ruff detectaram a falha em todas as tentativas. O fluxo terminou em `CODEX_REVIEW`, criou o pacote de escalamento e nao chamou automaticamente o Codex.

Depois de um primeiro ensaio sem limite global ter bloqueado o WSL, foram adicionadas tres proteccoes: timeout por operacao, timeout global do fluxo e watchdog externo do processo. A repeticao final terminou em 25,7 segundos. A telemetria observada na M4000 foi 2367 MiB de 8192 MiB e 41 graus Celsius, sem erro CUDA ou falta de memoria.
