# ODIN Dashboard Visual QA Report

- Status: **PASS**

## Endpoint Checks
- /: 200 ok=True
- /runtime: 200 ok=True
- /mt5: 200 ok=True
- /atlas: 200 ok=True
- /assistant: 200 ok=True
- /llm/status: 200 ok=True
- /logs: 200 ok=True

## Critical Tokens
- TRADING REAL: BLOCKED: present=True
- MT5 ORDER_SEND: BLOCKED: present=True
- BROKER REAL: BLOCKED: present=True
- ATLAS: SHADOW_ONLY: present=True
- LLM: READ_ONLY: present=True
- Perguntar ao ODIN: present=True
- RISK ENGINE: present=True
- POSITIONS: present=True
- EVENTS: present=True
- ASSISTANT: present=True
- COMMAND BAR: present=True
- SPARKLINE: present=True
- MARKET INTELLIGENCE: present=True
- forbidden::ENABLE_REAL_TRADING: present=False
- forbidden::DIRECT_ORDER_SEND: present=False
- forbidden::MT5_ORDER_SEND: present=False
- forbidden::BROKER_REAL_EXECUTION: present=False
- forbidden::Activa trading real: present=False
- forbidden::Abrir ordem: present=False
- forbidden::Fechar posição: present=False
