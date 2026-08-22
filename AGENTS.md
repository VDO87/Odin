# ODIN — regras operacionais permanentes

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

## Limites inegociáveis

- Proibir `mt5.order_send` fora da exceção RC1 descrita abaixo; não enviar ordens
  reais nem automatizar XTB.
- Não alterar guardrails autonomamente. Na ausência de uma condição segura, falhar fechado.
- Não fabricar dados, resultados ou proveniência; não ler, criar ou expor credenciais reais.
- Risk vence Hermes; Treasury vence Hermes em matéria de dinheiro; Hermes permanece read-only.
- O Dashboard nunca indica "pronto para real" se Core ou Risk estiver bloqueado.
- Não instalar dependências, usar `sudo` ou apagar ficheiros existentes sem confirmação humana explícita.

## Método de trabalho

- Antes de trabalho significativo, ler `docs/ODIN_ESTADO_CANONICO_E_PLANO.md`; usar a respetiva Definition of Done para concluir a baseline. Se faltar ou estiver ambíguo, parar e pedir decisão humana.
- Diagnosticar antes de corrigir; não remover testes para obter verde nem mascarar leaks aumentando limites indefinidamente.
- Preservar trabalho existente. Não usar `git reset --hard`, `git push --force` ou merge automático.
- Podem ser resolvidas autonomamente pequenas alterações técnicas, reversíveis e dentro do objetivo ativo; cada correção exige validação proporcional.
- Criar checkpoint Git após um estado estável e validado. Não aumentar o escopo enquanto existir objetivo ativo.
- Não repetir indefinidamente: exigir nova evidência antes de repetir uma tentativa; escalar após tentativas esgotadas.
- Parar perante credenciais, licenciamento ambíguo, operação destrutiva, risco de perda de dados ou necessidade de alterar guardrails.

## Exceção estrita — ODIN DEMO EXECUTION RC1

- A infraestrutura pode conter no máximo uma chamada `mt5.order_send`, apenas
  em `src/odin/adapters/mt5/demo_execution_adapter.py` e apenas atrás do Demo
  Execution Gate.
- A exceção permite construir e testar offline a infraestrutura. Não autoriza
  executar a primeira ordem DEMO. O CANARY exige confirmação humana específica
  depois de um PRE-FLIGHT completo.
- Antes da chamada, o gate tem de provar deterministicamente conta DEMO,
  broker/server/login esperados, EURUSD, Risk aprovado, dados frescos,
  reconciliação OK, kill switch desligado, limites/margem/stops válidos,
  idempotência e confirmação canary one-shot.
- Conta REAL, modo UNKNOWN, identidade divergente, falta de evidência ou
  fallback para outra conta implicam `HARD_BLOCK` antes de `order_send`.
- `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`
  permanecem globais. Uma permissão DEMO é separada, limitada, auditável,
  não persistente e nunca pode promover ou reutilizar autoridade para REAL.
- Hermes, n8n, LLM, Strategy, Risk e qualquer módulo fora do adapter isolado
  continuam tecnicamente proibidos de chamar `order_send`.
- Toda execução DEMO futura tem de ser idempotente e ligada ao Decision Ledger
  e Execution Ledger. Não fazer merge automático desta branch.
