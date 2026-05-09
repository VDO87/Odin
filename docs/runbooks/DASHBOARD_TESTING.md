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
- ATLAS visível
- LLM visível
- Risk Engine visível
- posições visíveis
- logs visíveis
- campo Perguntar ao ODIN visível
- comandos perigosos ausentes

## 6) Critério
- operador percebe estado do ODIN em menos de 30 segundos.
