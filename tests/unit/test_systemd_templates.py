from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_systemd_templates_exist_and_are_safe() -> None:
    template_files = [
        ROOT / "services/odin-runtime.service.template",
        ROOT / "services/odin-dashboard.service.template",
        ROOT / "services/odin-telegram.service.template",
    ]
    for path in template_files:
        assert path.exists(), str(path)
        text = path.read_text(encoding="utf-8")
        assert "ENABLE_REAL_TRADING=false" in text
        assert "MT5_ORDER_SEND_ENABLED=false" in text
        assert "BROKER_ALLOW_REAL_EXECUTION=false" in text
