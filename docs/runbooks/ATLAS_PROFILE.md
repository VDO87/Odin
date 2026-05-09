# ATLAS Profile Runbook

## 1) ATLAS interno do ODIN
ATLAS é a camada de análise/consenso do ODIN, sem execução directa.

## 2) ATLAS-lite
Agentes activos:
- market_agent
- technical_agent
- risk_agent
- critic_agent

## 3) ATLAS-full
Inclui todos os agentes definidos no `odin_atlas/agents/`.

## 4) Recomendação
- Runtime normal: `ATLAS_PROFILE=lite`
- Análise manual detalhada: `ATLAS_PROFILE=full`

## 5) Segurança
- Ambos os perfis permanecem `SHADOW_ONLY`.
- Nenhum perfil executa ordens.
