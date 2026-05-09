# LOCAL_LLM_RUNTIME (ODIN RC1.3)

## 1. O que é o LLM local no ODIN
É a integração opcional de um modelo local (provider `ollama`) para suporte de respostas operacionais no Assistant.

## 2. Para que serve
- Responder perguntas do operador.
- Explicar estado do sistema.
- Resumir risco.
- Explicar consenso/estado do ATLAS.
- Explicar MT5 Shadow.
- Gerar notas operacionais curtas.

## 3. O que não pode fazer
- Executar ordens.
- Activar trading real.
- Alterar configurações críticas.
- Ignorar o Risk Engine.
- Ignorar o Command Bus.

## 4. Como configurar .env
Variáveis principais:
- `LOCAL_LLM_ENABLED=true`
- `LOCAL_LLM_PROVIDER=ollama`
- `LOCAL_LLM_BASE_URL=http://127.0.0.1:11434`
- `LOCAL_LLM_MODEL=`
- `LOCAL_LLM_TIMEOUT_SECONDS=30`
- `OPENAI_SUPPORT_ENABLED=false`

Sem `LOCAL_LLM_MODEL`, o healthcheck LLM fica `WARNING` e o Assistant usa fallback.

## 5. Como testar
```bash
./run_odin.sh --smoke-test
python -m apps.dashboard_terminal.cli llm-status
python -m apps.dashboard_terminal.cli ask "Qual é o estado do ODIN?"
python -m apps.dashboard_html.app --smoke-test
python -m apps.telegram_bot.bot --dry-run
```

## 6. Como interpretar estados
- `OK`: LLM local acessível e modelo configurado.
- `WARNING`: LLM não configurado/indisponível; fallback ativo.
- `BLOCKED`: apenas se for marcado como obrigatório no ambiente.
- `CRITICAL`: erro estrutural grave.

## 7. Como funciona fallback
Quando o LLM local falha ou não está configurado, o Assistant responde via fallback seguro com contexto estruturado e nunca executa acções diretas.

## 8. Como funciona redacção de segredos
Antes de enviar contexto ao LLM e antes de gravar logs do Assistant, tokens/passwords/API keys são mascarados (`***REDACTED***`).

## 9. OpenAI no futuro
OpenAI está `OFF` por defeito em RC1.3.
Se for activado no futuro, deve ficar restrito a segunda opinião e sempre auditado.
