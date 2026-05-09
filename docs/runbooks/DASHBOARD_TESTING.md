# Dashboard Testing Runbook

## 1) Testar dashboard HTML
```bash
./run_odin.sh --dashboard
```

## 2) Abrir dashboard
- `http://127.0.0.1:8000`

## 3) Gerar preview
```bash
./run_odin.sh --dashboard-preview
./run_odin.sh --dashboard-qa
python -m apps.dashboard_html.app --export-preview
python -m apps.dashboard_html.app --dashboard-qa
```

## 4) Testar dashboard TUI
```bash
./run_odin.sh --tui-demo
./run_odin.sh --tui-once
./run_odin.sh --tui-smoke-test
```

## 5) Checklist visual
- top bar visível
- runtime state visível
- trading real bloqueado visível
- MT5 visível
- sparkline/market chart visível
- `DEMO DATA` visível quando não há snapshot real
- Market Intelligence visível
- ATLAS visível
- LLM visível
- Risk Engine visível
- posições visíveis
- logs visíveis
- campo Perguntar ao ODIN visível
- command bar visível (apenas comandos seguros)
- comandos perigosos ausentes

## 6) RC1.6.1 comandos rápidos do painel Assistant
- Estado
- Posso operar?
- MT5
- ATLAS
- Risco
- Logs

## 7) Critério
- operador percebe estado do ODIN em menos de 30 segundos.
