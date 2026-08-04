# ODIN TradeDesk — operador DEMO

## Objetivo e limites

Este ambiente permite observar uma conta MT5 **DEMO** e dados públicos, manter um registo local e testar o ecrã de investimento. Não envia ordens, não produz recomendações financeiras e não liga trading real. Os três bloqueios devem permanecer `false`: `safe_to_trade`, `real_trading` e `execution_allowed`.

## Utilização diária

1. Abra `ODIN TradeDesk (Demo)` no Ambiente de Trabalho. A página local abre em `http://127.0.0.1:8765/`.
2. Abra `ODIN Refresh DEMO Observations` para fazer uma recolha manual limitada. O fluxo recolhe a conta/posições/cotação MT5 DEMO em leitura, atualiza a observação ECB, persiste um ciclo shadow sem decisão, compara a frescura/histórico de recolhas e guarda relatórios locais.
3. Atualize a página TradeDesk. Confirme `MT5 DEMO = CONNECTED_DEMO_READ_ONLY`, a moeda da conta, o timestamp de EURUSD e `Execution = false`.
4. Leia o gráfico: `MT5 DEMO M15` significa velas do terminal; `local replay` significa dados simulados. Os resultados, posições e diário de **replay** não pertencem à conta MT5.
5. Abra `Technical cockpit` para saúde de ODIN/Hermes, recursos, eventos, frescura de dados e última observação MT5.

O TradeDesk também mostra a última `shadow observation`. Este é apenas um registo de que as entradas observacionais estavam frescas; o estado esperado é `OBSERVED_NO_DECISION`, com decisão, proposta e execução em `false`.

## Onde ficam os registos

- Estado MT5 DEMO sanitizado: `D:\ODIN_LOCAL\runtime\mt5_demo_readonly.json`.
- Auditoria de recolhas MT5: `D:\ODIN_LOCAL\logs\mt5_demo_readonly.jsonl`.
- Dados públicos e proveniência: `D:\ODIN_LOCAL\cache\public` e `D:\ODIN_LOCAL\logs\public_data_events.jsonl`.
- Relatórios: `D:\ODIN_LOCAL\reports`.

O relatório `odin-shadow-observation-*.json` é factual: compara a frescura das
fontes e contabiliza recolhas/falhas. Não interpreta preços, não cria decisões
e não permite execução.

Estes ficheiros não devem incluir palavra-passe ou outras credenciais. A configuração local fica no `.env` ignorado pelo Git dentro do WSL.

## Verificação antes de confiar numa observação

- A hora da cotação deve ser recente e o estado deve ser `CONNECTED_DEMO_READ_ONLY`. Após 15 minutos sem recolha, ODIN trata a observação MT5 como bloqueada; execute a atualização manual em vez de assumir que a informação antiga continua válida.
- A fonte pública deve mostrar `OK` e `Data fresh = true`.
- O cockpit não deve indicar alertas críticos, temperatura elevada ou indisponibilidade do runtime.
- A secção Hermes é apenas diagnóstico local; a evidência é não confiável para decisão e não é um sinal de mercado.

## Paragem segura

Se houver falha de terminal, dados antigos, temperatura CPU/GPU igual ou superior a 80°C, erro CUDA ou falta de memória, pare a recolha e mantenha o TradeDesk em observação. A atualização manual verifica a GPU antes de cada etapa e bloqueia a 80°C; também bloqueia se uma sonda térmica CPU do Windows reportar 80°C ou mais. Não tente contornar os bloqueios nem introduza ordens pela aplicação. O operador deve investigar os registos e restaurar apenas uma recolha read-only saudável.
