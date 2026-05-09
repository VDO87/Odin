# ODIN RC1.7 Deployment Package Report

## 1. Estado inicial
- Branch: `release/rc1`
- Base: `v0.1.6.2-rc1-dashboard-readability`
- Commit inicial: `2d4fee7`

## 2. Estrutura ODIN_RUNTIME
- Definida em `odin_deploy/paths.py` e usada pelos scripts RC1.7.

## 3. Scripts criados
- `scripts/install_odin_runtime.sh`
- `scripts/update_odin_runtime.sh`
- `scripts/uninstall_odin_runtime.sh`
- `scripts/backup_odin_runtime.sh`
- `scripts/restore_odin_runtime.sh`
- `scripts/check_llm_runtime.sh`
- `scripts/check_atlas_profile.sh`
- `scripts/validate_odin_runtime.sh`
- `scripts/build_release_package.sh`

## 4. Install dry-run
- `./scripts/install_odin_runtime.sh --dry-run` -> OK
- `./scripts/install_odin_runtime.sh --odin-home /tmp/ODIN_RUNTIME_TEST --dry-run` -> OK

## 5. Update dry-run
- `./scripts/update_odin_runtime.sh --dry-run --backup-first` -> OK

## 6. Uninstall dry-run
- `./scripts/uninstall_odin_runtime.sh --dry-run` -> OK

## 7. Backup/restore
- Implementado via `odin_deploy/backup.py` + scripts shell.

## 8. Systemd templates
- `services/odin-runtime.service.template`
- `services/odin-dashboard.service.template`
- `services/odin-telegram.service.template`
- `services/ollama-override.example`

## 9. LLM readiness
- `scripts/check_llm_runtime.sh`
- Atualizado `docs/runbooks/LLM_INSTALLATION_READINESS.md`

## 10. ATLAS readiness
- `scripts/check_atlas_profile.sh`
- Atualizado `docs/runbooks/ATLAS_PROFILE.md`

## 11. Runtime validator
- `odin_deploy/validator.py`
- `scripts/validate_odin_runtime.sh`
- Saídas:
  - `ODIN_HOME/data/runtime/install_validation_report.json`
  - `docs/reports/ODIN_RC1_7_INSTALL_VALIDATION_REPORT.md`

## 12. Package build
- `scripts/build_release_package.sh`
- Saída: `dist/odin-rc1.7-deployment-package.tar.gz`

## 13. Testes
- `pytest -q` -> `246 passed`
- `ruff check .` -> passed
- `mypy .` -> passed
- `./scripts/validate_odin_runtime.sh --odin-home /tmp/ODIN_RUNTIME_TEST --dry-run` -> PASS
- `python -m apps.dashboard_html.app --dashboard-qa` -> PASS
- `./run_odin.sh --soak-test-mini` -> PASS

## 14. Segurança
- Trading real permanece bloqueado.
- `MT5 order_send` permanece bloqueado.
- `BROKER_ALLOW_REAL_EXECUTION=false` mantido.
- `OPENAI_SUPPORT_ENABLED=false` por defeito.

## 15. Como instalar no PC
```bash
./scripts/install_odin_runtime.sh --odin-home ~/ODIN_RUNTIME
```

## 16. Package gerado
- `dist/odin-rc1.7-deployment-package.tar.gz`

## 17. Segurança confirmada
- `ENABLE_REAL_TRADING=false`
- `MT5_ORDER_SEND_ENABLED=false`
- `XTB_REAL_ENABLED=false`
- `BROKER_ALLOW_REAL_EXECUTION=false`
- `OPENAI_SUPPORT_ENABLED=false`
