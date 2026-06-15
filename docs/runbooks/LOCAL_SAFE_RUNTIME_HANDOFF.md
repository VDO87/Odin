# Local Safe Runtime Handoff

## Como validar o runtime

Executar a validacao agregada e a suite de testes a partir da raiz do repositorio:

```bash
python3 -m odin.cli smoke
python3 -m unittest discover -s tests -v
```

Resultado esperado: smoke `PASS`, `all_modules_ok=true`, `safe_state_confirmed=true`, `blocking_state_confirmed=true` e testes todos OK.

## Como arrancar o dashboard

```bash
python3 -m odin.cli dashboard --host 127.0.0.1 --port 8765
```

## Endpoints disponiveis

- `/health`
- `/state`
- `/risk/status`
- `/hermes/status`
- `/hermes/summary`
- `/treasury/status`
- `/market/status`
- `/market/watch`
- `/data/quality`
- `/feed/source`
- `/strategy/status`
- `/decision/intent`
- `/risk/gate`
- `/shadow/proposal`
- `/mt5/bridge`
- `/mt5/symbols`
- `/mt5/feed`
- `/mt5/feed/quality`
- `/runtime/smoke`
- `/logs/tail`

## Como parar dashboard

Usar `Ctrl+C`.

Resultado esperado:

```text
ODIN dashboard stopped
```

## Permitido na proxima fase

- Criar contrato/adaptador mock para uma futura bridge MT5.
- Expor endpoint/status mock da bridge.
- Validar `python3 -m odin.cli mt5-bridge`.
- Validar `python3 -m odin.cli mt5-symbols`.
- Validar `python3 -m odin.cli mt5-feed`.
- Validar `python3 -m odin.cli mt5-feed-quality`.
- Validar `python3 -m odin.cli feed-source`.
- Manter o smoke local em `PASS`.
- Reforcar documentacao, testes e bloqueios de seguranca.
- Continuar sem integracao real de broker.

## Proibido na proxima fase

- Ligar a MetaTrader5 real.
- Fazer login em conta MT5.
- Chamar `mt5.order_send`.
- Criar XTB API.
- Criar Telegram.
- Criar sinais BUY/SELL.
- Criar `entry`, `stop_loss` ou `take_profit`.
- Criar position sizing.
- Alterar `safe_to_trade`, `real_trading` ou `execution_allowed` para permitir execucao.
