# ODIN DEMO — walkthrough supervisionado

## Limite inalterável

Esta baseline é observacional e local. Antes, durante e depois de cada passo,
confirme `safe_to_trade=false`, `real_trading=false` e
`execution_allowed=false`. Não introduza ordens, credenciais em comandos ou
alterações de configuração para contornar um bloqueio.

## Arranque e verificação

1. Inicie Windows e confirme que o terminal **OANDA TMS MT5 DEMO** já está aberto.
2. Inicie WSL e abra o repositório em `/home/odin/projects/odin`.
3. Inicie apenas os componentes locais necessários pelo atalho aprovado.
4. Abra o atalho **ODIN TradeDesk (Demo)**; deve abrir `http://127.0.0.1:8765/`.
5. Abra `/cockpit` no mesmo host local.
6. Confirme no cockpit que ODIN não apresenta bloqueio crítico.
7. Confirme `MT5 DEMO = CONNECTED_DEMO_READ_ONLY`; nunca trate DEMO como real.
8. Confirme Hermes como diagnóstico local read-only, sem autoridade financeira.
9. Confirme o runtime Ollama e recursos; pare se houver alerta térmico/crítico.
10. Em market data, confirme o manifesto validado EURUSD M15 e o hash RAW ligado.
11. Use somente **ODIN Refresh DEMO Observations** para refresh manual limitado.
12. Execute replay apenas como `SIMULAÇÃO / REPLAY`; resultados não pertencem à conta MT5.
13. Consulte os relatórios em `D:\ODIN_LOCAL\reports` e os eventos sanitizados.
14. Para parar, feche os componentes locais; não criar processo persistente nem serviço automático.

## Paragem segura

Perante terminal desligado, dados antigos, falha de redaction, alerta de CPU/GPU
ou qualquer guardrail diferente de `false`, pare a recolha e mantenha o sistema
em observação. Investigue logs sanitizados; não tente preencher dados nem enviar
qualquer ordem.
