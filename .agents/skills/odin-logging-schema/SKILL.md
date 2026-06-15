---
name: odin-logging-schema
description: Usar para definir eventos, logs JSONL, auditoria e SQLite. Nao usar para guardar secrets ou dados sensiveis sem politica.
---

# Odin Logging Schema

- Usar JSONL para eventos auditaveis.
- Usar SQLite para estado local quando houver modulos funcionais.
- Cada evento deve ter timestamp, origem, tipo, severidade e correlacao.
- Nao registar secrets, tokens ou credenciais.
- Logs devem permitir explicar decisoes e bloqueios.
