from __future__ import annotations

from pathlib import Path

from odin_deploy.paths import DeployPaths


RUNTIME_TEMPLATE = """[Unit]
Description=ODIN Runtime (RC1 Safe Shadow)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={app_dir}
Environment=ODIN_HOME={odin_home}
Environment=ENABLE_REAL_TRADING=false
Environment=ENABLE_AUTO_EXECUTION=false
Environment=MT5_ORDER_SEND_ENABLED=false
Environment=BROKER_ALLOW_REAL_EXECUTION=false
ExecStart={app_dir}/run_odin.sh --runtime
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


DASHBOARD_TEMPLATE = """[Unit]
Description=ODIN Dashboard (RC1 Safe Shadow)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={app_dir}
Environment=ODIN_HOME={odin_home}
Environment=ENABLE_REAL_TRADING=false
Environment=MT5_ORDER_SEND_ENABLED=false
Environment=BROKER_ALLOW_REAL_EXECUTION=false
ExecStart={app_dir}/run_odin.sh --dashboard
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


TELEGRAM_TEMPLATE = """[Unit]
Description=ODIN Telegram Bot (RC1 Safe Shadow)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={app_dir}
Environment=ODIN_HOME={odin_home}
Environment=ENABLE_REAL_TRADING=false
Environment=MT5_ORDER_SEND_ENABLED=false
Environment=BROKER_ALLOW_REAL_EXECUTION=false
ExecStart={venv_python} -m apps.telegram_bot.bot
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def render_service_templates(paths: DeployPaths) -> dict[str, str]:
    values = {
        "odin_home": str(paths.odin_home),
        "app_dir": str(paths.app_dir),
        "venv_python": str(paths.venv_dir / "bin" / "python"),
    }
    return {
        "odin-runtime.service.template": RUNTIME_TEMPLATE.format(**values),
        "odin-dashboard.service.template": DASHBOARD_TEMPLATE.format(**values),
        "odin-telegram.service.template": TELEGRAM_TEMPLATE.format(**values),
    }


def write_service_templates(paths: DeployPaths, destination: Path | None = None) -> list[Path]:
    target = destination or paths.services_dir
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, content in render_service_templates(paths).items():
        path = target / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
