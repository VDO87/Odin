# Hermes Supervisor Operations

## Objetivo

Fornecer uma base operacional para o Hermes atuar como supervisor local-first do projeto `ODIN_HERMES_ALIVE`, mantendo sempre:

- `REAL_TRADING=false`
- `SAFE_TO_TRADE=false`
- `execution_allowed=false`

## Comandos

Validar runtime seguro:

```bash
python3 -m odin.cli validate
```

Executar um ciclo do supervisor Hermes:

```bash
python3 -m odin.cli hermes-supervisor
```

Executar o smoke atualizado:

```bash
python3 -m odin.cli smoke
```

Dashboard runtime:

- `GET /hermes/runtime`

## O que o supervisor faz nesta fase

- regista agentes permanentes;
- regista a biblioteca inicial de skills;
- persiste objetivo operacional bootstrap;
- grava memoria operacional e de projeto;
- cria checkpoints;
- diagnostica disponibilidade de `ollama`, `codex`, GPU probe e Telegram;
- aplica routing local-first, com cloud e Codex apenas como fallback;
- mantem o sistema em modo degradado quando faltam dependencias locais.

## Limitacoes atuais

- nao ativa trading real;
- nao faz merge, push ou alteracoes destrutivas;
- nao arranca um daemon infinito por defeito;
- nao envia Telegram sem `TELEGRAM_BOT_TOKEN`;
- nao usa Ollama enquanto o binario ou modelos locais nao estiverem realmente disponiveis.
