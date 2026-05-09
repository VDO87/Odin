# ODIN Session Handoff

## 1. Estado actual
- Branch: `release/rc1`
- Commit mais recente de referência RC1.8: `c418cb9`
- Tag mais recente: `v0.1.8-rc1-local-runtime-install`
- Package mais recente: `dist/odin-rc1.7-deployment-package.tar.gz`
- Instalação real: `~/ODIN_RUNTIME`
- Working tree: verificar com `git status --short --branch`
- GitHub sync: `origin/release/rc1`

## 2. Como retomar amanhã
```bash
cd ~/ODIN_RUNTIME/app
./run_odin.sh --dashboard
./run_odin.sh --tui-demo
./run_odin.sh --runtime-validate
./run_odin.sh --soak-test-mini
```

## 3. Validação do repositório
```bash
cd /home/vdo/Secretária/Projects_Codex/Odin_Teste
git status --short --branch
git pull origin release/rc1
pytest -q
```

## 4. Próxima tarefa
- RC1.9 Real Service & Reboot Recovery Test

## 5. Regras para amanhã
- Não activar trading real
- Não activar MT5 order_send
- Não configurar credenciais reais sem checklist
- Não activar systemd sem teste manual
- Não avançar para estratégias antes de recovery/reboot estar validado

## 6. Comandos úteis
```bash
./run_odin.sh --dashboard
./run_odin.sh --dashboard-preview
./run_odin.sh --dashboard-qa
./run_odin.sh --tui-demo
./run_odin.sh --runtime-validate
./run_odin.sh --soak-test-mini
./scripts/check_llm_runtime.sh --odin-home ~/ODIN_RUNTIME
./scripts/check_atlas_profile.sh --odin-home ~/ODIN_RUNTIME
./scripts/backup_odin_runtime.sh --odin-home ~/ODIN_RUNTIME
```
