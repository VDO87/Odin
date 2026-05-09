# ODIN RC1.7 Install Guide

## 1) Requisitos
- Python 3.12+
- `bash`
- Acesso de escrita a `~/ODIN_RUNTIME` (ou caminho alternativo)
- Opcional: wheelhouse local em `vendor/wheels` para instalação offline

## 2) Instalação rápida
```bash
./scripts/install_odin_runtime.sh --odin-home ~/ODIN_RUNTIME
```

## 3) Instalação dry-run
```bash
./scripts/install_odin_runtime.sh --dry-run
./scripts/install_odin_runtime.sh --odin-home /tmp/ODIN_RUNTIME_TEST --dry-run
```

## 4) Instalação offline
```bash
./scripts/install_odin_runtime.sh --odin-home ~/ODIN_RUNTIME --offline
```
Requer wheels locais em `ODIN_RUNTIME/vendor/wheels` (ou no projecto antes da cópia).

## 5) Configurar `.env`
- Ficheiros de runtime:
  - `ODIN_RUNTIME/config/.env`
  - `ODIN_RUNTIME/config/.env.example`
- O instalador cria backup se `.env` já existir.
- Não guardar segredos no repositório.

## 6) Testar dashboard HTML
```bash
~/ODIN_RUNTIME/app/run_odin.sh --dashboard-preview
~/ODIN_RUNTIME/app/run_odin.sh --dashboard-qa
```

## 7) Testar TUI
```bash
~/ODIN_RUNTIME/app/run_odin.sh --tui-smoke-test
```

## 8) Validar runtime
```bash
~/ODIN_RUNTIME/app/scripts/validate_odin_runtime.sh --odin-home ~/ODIN_RUNTIME
```

## 9) Validar LLM local
```bash
~/ODIN_RUNTIME/app/scripts/check_llm_runtime.sh
```

## 10) Validar perfil ATLAS
```bash
~/ODIN_RUNTIME/app/scripts/check_atlas_profile.sh
```

## 11) Backup
```bash
./scripts/backup_odin_runtime.sh --odin-home ~/ODIN_RUNTIME
```

## 12) Update
```bash
./scripts/update_odin_runtime.sh --odin-home ~/ODIN_RUNTIME --backup-first
```

## 13) Uninstall (seguro)
```bash
./scripts/uninstall_odin_runtime.sh --odin-home ~/ODIN_RUNTIME --dry-run
```
Sem `--dry-run`, pede confirmação.

## 14) systemd opcional
- Templates disponíveis em:
  - `services/odin-runtime.service.template`
  - `services/odin-dashboard.service.template`
  - `services/odin-telegram.service.template`
- Não é executado `systemctl` automaticamente.

## 15) Segurança (obrigatória)
- Trading real bloqueado.
- `MT5 order_send` bloqueado.
- Broker real bloqueado.
- XTB real bloqueado.
- LLM e ATLAS sem execução directa.
