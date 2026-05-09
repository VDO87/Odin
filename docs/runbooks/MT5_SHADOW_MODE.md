# MT5 Shadow Mode (ODIN RC1.2)

## 1) O que é MT5 Shadow Mode
MT5 Shadow Mode é um modo de diagnóstico e leitura no qual o ODIN apenas observa dados do MetaTrader 5, sem executar ordens nem alterar posições.

## 2) O que o ODIN pode fazer
- Ler ticks.
- Ler candles.
- Ler posições.
- Reconciliar posições entre MT5 e registry do ODIN.
- Mostrar estado MT5 no dashboard/CLI/assistant.
- Alimentar Assistant e ATLAS com contexto de mercado shadow.

## 3) O que o ODIN não pode fazer
- Enviar ordens (`order_send`).
- Fechar posições.
- Modificar SL/TP.
- Activar trading real.

## 4) Como configurar `.env`
Definir no mínimo:
- `ODIN_MODE=SHADOW_MT5`
- `MT5_ENABLED=true`
- `MT5_SHADOW_MODE=true`
- `MT5_ORDER_SEND_ENABLED=false`
- `MT5_ALLOW_POSITION_MODIFICATION=false`
- `MT5_ALLOW_POSITION_CLOSE=false`
- `BROKER_ALLOW_REAL_EXECUTION=false`

Não colocar passwords no código. Usar `.env` local quando necessário.

## 5) Como testar
```bash
./healthcheck.sh --offline-ok
./run_odin.sh --smoke-test
python -m apps.dashboard_terminal.cli mt5-status
python -m apps.dashboard_terminal.cli mt5-positions
python -m apps.dashboard_html.app --smoke-test
```

## 6) Como interpretar estados
- `OK`: leitura MT5 funcional e sem bloqueios críticos.
- `WARNING`: degradação tolerável para diagnóstico.
- `BLOCKED`: não seguro para operar (shadow continua para diagnóstico).
- `CRITICAL`: erro estrutural grave.

## 7) O que fazer se...
- MT5 não estiver instalado:
  - Confirmar que o sistema permanece vivo.
  - Esperar `WARNING/BLOCKED` em healthcheck MT5.
- terminal não inicializar:
  - Validar instalação do terminal e permissões.
- login não estiver configurado:
  - Operar apenas em diagnóstico até configurar ambiente.
- houver posição sem SL/TP:
  - Esperar `UNPROTECTED_POSITION` e estado recomendado `BLOCKED`.
- houver posição externa:
  - Esperar `EXTERNAL_POSITION` e alerta operacional.
- houver magic number desconhecido:
  - Esperar `UNKNOWN_MAGIC` e bloqueio se política exigir.
