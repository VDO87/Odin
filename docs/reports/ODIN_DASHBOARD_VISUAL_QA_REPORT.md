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
- Runtime: present=True
- Risk: present=True
- Positions: present=True
- Events: present=True
- forbidden::ENABLE_REAL_TRADING: present=False
- forbidden::DIRECT_ORDER_SEND: present=False
- forbidden::MT5_ORDER_SEND: present=False
- forbidden::BROKER_REAL_EXECUTION: present=False
