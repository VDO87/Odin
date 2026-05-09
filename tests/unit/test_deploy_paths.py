from __future__ import annotations

from odin_deploy.paths import resolve_deploy_paths


def test_deploy_paths_default_home() -> None:
    paths = resolve_deploy_paths()
    assert str(paths.odin_home).endswith("ODIN_RUNTIME")
    assert paths.app_dir.name == "app"
    assert paths.venv_dir.name == ".venv"


def test_deploy_paths_custom_home() -> None:
    paths = resolve_deploy_paths("/tmp/ODIN_RUNTIME_TEST_CASE")
    assert str(paths.odin_home) == "/tmp/ODIN_RUNTIME_TEST_CASE"
    assert str(paths.config_dir).endswith("/tmp/ODIN_RUNTIME_TEST_CASE/config")
