# Segredos, rotação e recuperação

## Limite operacional

Segredos permanecem fora do Git e fora de `D:\ODIN_LOCAL`: usar apenas o
`.env` local ignorado pelo Git ou o armazenamento seguro já configurado no
Windows. Nunca incluir os valores em comandos, pedidos, screenshots, JSONL,
SQLite, relatórios, HTML, respostas localhost ou diagnósticos Hermes.

## Rotação ou suspeita de exposição

1. Pare qualquer recolha manual; mantenha `safe_to_trade=false`,
   `real_trading=false` e `execution_allowed=false`.
2. Revogue/rode as credenciais no fornecedor, fora deste repositório.
3. Atualize somente o armazenamento local seguro; não cole os valores em logs.
4. Execute os testes de redaction e reveja apenas nomes de campos/indicadores
   `[REDACTED]`, não os valores de segredos.
5. Só retome a recolha MT5 DEMO read-only depois de confirmar o kill switch e
   uma observação nova e reconciliada.

## Emergência e recuperação

O kill switch é independente de Hermes/LLM. Com erro, dados stale, temperatura
CPU/GPU >= 80 °C, falha de integridade ou dúvida de credenciais: parar o refresh
manual, preservar a evidência sanitizada e investigar sem ativar execução.
Recuperação significa restaurar uma observação local saudável; não inclui ordens
MT5, ordem DEMO, depósitos ou alteração dos guardrails.
