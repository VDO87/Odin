# ODIN RC1 Install

## Instalar
```bash
./install.sh
```

## Configurar
1. Copiar `.env.example` para `.env`.
2. Preencher credenciais demo (nunca real no RC1).

## Arrancar
```bash
./run_odin.sh
```

## Parar
- `Ctrl+C` no processo do dashboard.

## Dashboard
- URL: `http://127.0.0.1:8000`
- Páginas: `/`, `/atlas`, `/logs`

## Telegram
- Estrutura em `apps/telegram_bot/bot.py`.
- Restringido a `TELEGRAM_ALLOWED_USER_IDS`.

## Healthcheck
```bash
./healthcheck.sh
```

## Avisos de segurança
- Trading real bloqueado por default.
- `MT5 order_send` bloqueado.
- `XTB real` bloqueado.
- `BrokerRouter place_order` bloqueado se `BROKER_ALLOW_REAL_EXECUTION=false`.
- LLM e ATLAS sem execução directa.
