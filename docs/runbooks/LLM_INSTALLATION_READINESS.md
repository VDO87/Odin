# LLM Installation Readiness (RC1.7)

## 1) LLM local recomendado
- Provider recomendado: Ollama.

## 2) Instalação automática
- O ODIN RC1.7 **não instala Ollama automaticamente**.
- O ODIN RC1.7 **não instala modelos automaticamente**.
- O ODIN RC1.7 **não descarrega modelos automaticamente**.

## 3) Local de modelos
- `ODIN_MODELS_DIR=${ODIN_HOME}/models`
- `OLLAMA_MODELS=${ODIN_MODELS_DIR}/ollama`

## 4) Instalação manual de Ollama (operador)
1. Instalar Ollama manualmente no sistema operativo.
2. Confirmar binário:
   - `command -v ollama`
3. Confirmar endpoint:
   - `curl http://127.0.0.1:11434/api/tags`

## 5) Configuração e permissões
- Definir no `.env`:
  - `LOCAL_LLM_ENABLED=true`
  - `LOCAL_LLM_PROVIDER=ollama`
  - `LOCAL_LLM_BASE_URL=http://127.0.0.1:11434`
  - `LOCAL_LLM_MODEL=<modelo>`
- Garantir que o utilizador do runtime pode ler `ODIN_MODELS_DIR`.

## 6) Teste com ODIN
```bash
./scripts/check_llm_runtime.sh
python -m apps.dashboard_html.app --dashboard-qa
```

## 7) Fallback seguro
- Se LLM indisponível, o Assistant usa fallback.
- O sistema não deve crashar.
- OpenAI permanece OFF por defeito.
