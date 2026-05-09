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

## 6) Validação rápida
```bash
./scripts/check_atlas_profile.sh
```
Valida:
- `ATLAS_ENABLED`
- `ATLAS_PROFILE`
- `ATLAS_LITE_ENABLED`
- `ATLAS_FULL_ENABLED`
- lista de agentes do perfil
- `execution_permission=SHADOW_ONLY`
