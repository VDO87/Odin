# MT5 read-only — ODIN e Hermes

Este runbook limita a integração MetaTrader 5 a observação de dados. Não lê
`.env`, não aceita credenciais, não chama funções de trading e não escreve dados
de mercado. Os três guardrails são permanentes:

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

## Limites e fontes

- API: [MetaTrader5 Python Integration](https://www.mql5.com/en/docs/python_metatrader5).
- Ligação: `initialize(path)` e, em falha, `last_error()`; terminar sempre com
  `shutdown()`. A documentação MetaQuotes avisa que `initialize` pode lançar o
  terminal, pelo que a ferramenta ODIN bloqueia se o executável exato ainda não
  estiver em execução.
- Leituras permitidas: `terminal_info`, `account_info`, `symbol_info`,
  `copy_rates_range` e `copy_ticks_range`.
- Proibido: `login`, `order_send`, alteração de símbolo, subscrições, posições,
  ordens, depósitos, levantamentos, config do terminal e qualquer operação real.
- OANDA TMS: o guia oficial identifica MT5 como plataforma de terceiros e
  disponibiliza conta DEMO; os horários devem ser verificados por instrumento.
  Os símbolos do terminal podem divergir de `EUR_USD`: na instância ODIN
  observada, o alias é `EURUSD`.

## Ferramenta sanitizada

Em PowerShell, com o terminal DEMO já aberto:

```powershell
& \\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\scripts\windows\Inspect-ODIN-MT5-ReadOnly.ps1 `
  -TerminalPath 'C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe' `
  -Symbol EURUSD `
  -StartUtc '2026-07-01T00:00:00Z' `
  -EndUtc '2026-08-01T00:00:00Z'
```

A saída JSON contém somente: broker, server, estado do terminal, símbolo,
período, número de barras e classificação dos gaps. Nunca contém login,
password, token, saldo, posições, preços ou ticks individuais. Não grava
artefactos; a captura segura para P0 continua a exigir o pipeline de proveniência
e autorização própria.

## Política de gaps M1

1. `EXPECTED_GAP`: fecho semanal documentado; aceite e registado.
2. `NO_TICK_GAP`: `copy_ticks_range` devolve zero ticks estritamente entre as
   barras M1; aceitar com aviso, nunca criar candles.
3. `SUSPICIOUS_GAP`: há ticks nos minutos sem M1; marcar degradado e requerer
   revisão humana.
4. `INVALID_GAP`: UTC, ordem, OHLC ou classificação não verificável inválidos;
   bloquear.

O relatório é observacional, não uma aprovação P0. Hermes pode ler e resumir a
saída sanitizada, indicando a fonte e incerteza; não pode correr a ferramenta,
ler segredos, aprovar qualidade, risco ou execução.

## Diagnóstico limitado

| Sintoma | Ação segura |
| --- | --- |
| `initialize_failed` | Registar `last_error`, caminho e PID; não repetir sem evidência nova. |
| Várias instâncias MT5 | Confirmar caminho e command line; nunca terminar processos automaticamente. |
| Símbolo ausente | Usar apenas aliases documentados/observados, como `EURUSD`; não usar `symbol_select`. |
| `NO_TICK_GAP` | Registar no futuro manifesto; não forward-fill. |
| `SUSPICIOUS_GAP` | Parar a aceitação P0 e pedir revisão. |

## Estado ODIN observado em 2026-08-15

O terminal OANDA TMS ligado devolveu `EURUSD` M1 para julho de 2026. A análise
read-only encontrou fins de semana e minutos sem ticks, mas nenhum tick dentro de
um minuto sem barra. Isto é evidência de qualidade observacional, não licença,
proveniência completa nem aceitação P0.
