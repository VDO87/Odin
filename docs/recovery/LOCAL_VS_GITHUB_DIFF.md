# LOCAL VS GITHUB DIFF

Date: 2026-05-09
Local project: /home/vdo/Secretária/Projects_Codex/Odin_Teste
GitHub clone: /home/vdo/Secretária/Projects_Codex/Odin_Teste/Odin_GitHub_Check

## Clone status
- Clone succeeded on retry.
- Remote branch: main
- Remote HEAD: f35941a

## High-level comparison
- Local workspace contains a large RC1 foundation structure (src/, docs/, tests/, odin_*, apps/, logs/, scripts).
- GitHub repository has a different, smaller structure (core/, ai/, simulator/, strategies/, dashboard.py, main.py).

## Top-level entries only in local workspace
- .agents
- .codex
- .mypy_cache
- .pytest_cache
- .ruff_cache
- .venv
- .venv-f2
- INSTALL_ODIN.sh
- Odin_GitHub_Check
- Odin_Teste_BACKUP_20260509_120806
- README-INSTALL.md
- apps
- assets
- config
- dashboard-export-dash-action-5116ed6ff12a48f48649c9a8a0400a91.json
- docs
- healthcheck.sh
- install.sh
- logs
- odin
- odin_assistant
- odin_atlas
- odin_brain
- odin_brokers
- odin_control
- odin_core
- odin_execution
- odin_health
- odin_logs
- odin_market
- odin_risk
- odin_strategies
- pyproject.toml
- run_odin.sh
- runtime
- scripts
- src
- start_odin.sh
- systemd
- tools

## Top-level entries only in GitHub clone
- .pre-commit-config.yaml
- LICENSE
- __init__.py
- ai
- config.py
- core
- dashboard.py
- feedback.py
- main.py
- matplotlib
- metrics
- numpy.py
- pandas.py
- requests.py
- requirements.txt
- simulator
- strategies
- tracker.md
- trainer

## Notes
- A full file-by-file reconciliation should be done in a dedicated merge/migration step to avoid overwriting local RC1 work.
