# Dados públicos observacionais

## Limite operacional

O adaptador ECB usa apenas `https://data-api.ecb.europa.eu/service/data/EXR/` e uma
lista fechada de séries EUR. A implementação pede uma só observação CSV por chamada,
aplica timeout de 10 segundos por defeito, rejeita redirecionamentos e limita a resposta
a 2 MB.

Não há recomendação, sinal, proposta, decisão ou execução. A resposta pública é conteúdo
não confiável: ODIN guarda somente hash, comprimento, origem sanitizada e tempos. O conteúdo
não é mostrado no cockpit, persistido, nem encaminhado ao Hermes/LLM.

## Cache e prova

Defina `ODIN_PUBLIC_DATA_CACHE_DIR=/mnt/d/ODIN_LOCAL/cache/public` em `.env` local. Nunca
use uma chave na URL. O cache é endereçado pelo SHA-256 do conteúdo; uma resposta igual é
marcada como duplicada. Uma consulta falhada, origem fora da allowlist, resposta demasiado
grande ou conteúdo sem frescura suficiente deve manter o estado `BLOCKED` ou `WARNING`.

## Evidência antes de usar dados

1. Execute os testes `test_h7_public_observation.py` e `test_h8_ecb_exchange_rates.py`.
2. Confirme no relatório os eventos `public_data.cached`, `public_data.duplicate`,
   `public_data.failure` e `public_data.stale` conforme aplicável.
3. Valide fonte, timestamp e hash no cache local. Isto é uma verificação de integridade,
   não uma autorização para investimento ou execução.
