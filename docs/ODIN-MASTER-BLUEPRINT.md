# ODIN MASTER BLUEPRINT

## 1) Visão geral
ODIN é uma plataforma local de decisão, supervisão, aprendizagem por memória e execução assistida.
Não é apenas um bot.
Não é apenas um dashboard.
Não é apenas um LLM.

## 2) Blocos oficiais
- `odin_core`
- `odin_control`
- `odin_health`
- `odin_logs`
- `odin_assistant`
- `odin_atlas`
- `odin_brain`
- `odin_market`
- `odin_risk`
- `odin_execution`
- `odin_brokers`
- `odin_strategies/trading`
- `odin_strategies/fire`
- `apps/dashboard_html`
- `apps/dashboard_terminal`
- `apps/telegram_bot`

## 3) Modos oficiais
- `OFFLINE_REPLAY`
- `SHADOW_MT5`
- `TELEGRAM_SIGNAL`
- `XTB_DEMO_ASSISTED`
- `XTB_DEMO_AUTO`
- `XTB_REAL_ASSISTED`
- `XTB_REAL_LIMITED`

## 4) Estado alvo RC1
- Perfil alvo: `SHADOW_MT5 + TELEGRAM_SIGNAL`
- Sem trading real
- Sem execução automática real
- MT5 apenas sombra
- XTB apenas demo/assistido, quando adapter funcional existir

## 5) Regras de segurança
- Risk Engine obrigatório
- Command Bus obrigatório para acções
- logs obrigatórios
- reconciliação MT5 obrigatória
- recovery obrigatório após falha de rede ou reboot
- LLM não executa ordens
- ATLAS não executa ordens
