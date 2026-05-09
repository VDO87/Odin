# LLM Installation Readiness (RC1.6)

## 1) LLM local recomendado
- Provider recomendado: Ollama.

## 2) Instalação automática
- RC1.6 não instala modelos automaticamente.

## 3) Local de modelos
- `
${ODIN_MODELS_DIR}/ollama
`

## 4) Variável futura
- `OLLAMA_MODELS=${ODIN_MODELS_DIR}/ollama`

## 5) Binário/serviço Ollama
- O serviço Ollama pode residir fora da pasta ODIN por natureza do sistema operativo.

## 6) Detecção esperada no ODIN
- Ollama instalado.
- Endpoint disponível.
- Modelo configurado.
- Modelo ausente.
- Fallback seguro quando indisponível.

## 7) OpenAI
- OpenAI mantém-se OFF por defeito (`OPENAI_SUPPORT_ENABLED=false`).
