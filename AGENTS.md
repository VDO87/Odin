# Regras para Agentes Codex

Estas regras aplicam-se a qualquer trabalho feito neste repositorio.

## Principios

- Escrever codigo simples, modular e testavel.
- Separar Core, Risk, Treasury, Hermes e Dashboard.
- Documentar alteracoes relevantes em `CHANGELOG.md` ou em documentos de arquitectura.
- Criar testes sempre que forem criados modulos funcionais.
- Manter a documentacao em portugues de Portugal.

## Limites Nao Negociaveis

- Nao implementar execucao real de trading.
- Nao chamar `mt5.order_send`.
- Nao criar automacao de clique na XTB.
- Nao criar robos para enviar ordens XTB.
- Nao ler nem criar secrets reais.
- Nao criar ficheiros `.env` com chaves reais.
- Nao instalar dependencias novas sem confirmacao explicita.
- Nao usar `sudo`.
- Nao apagar ficheiros existentes sem confirmacao explicita.

## Arquitectura

- O Risk Engine vence sempre Hermes.
- O Treasury Engine vence sempre Hermes em materia de dinheiro.
- O Dashboard nunca pode mostrar "pronto para real" se Core ou Risk estiver bloqueado.
- Hermes deve permanecer read-only na fase inicial.
- Usar logs JSONL para eventos auditaveis.
- Usar SQLite para estado local auditavel quando existirem modulos funcionais.

## Modo de Trabalho

- Antes de alterar codigo, ler os documentos em `docs/` relevantes.
- Preferir contratos explicitos em `src/odin/contracts`.
- Manter adaptadores externos isolados em `src/odin/adapters`.
- Usar configuracao declarativa em `config/`.
- Nao introduzir dependencias sem explicar motivo, risco e alternativa sem dependencia.
