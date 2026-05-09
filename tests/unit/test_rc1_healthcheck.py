from odin_health.healthcheck import OdinHealthcheck


def test_healthcheck_returns_supported_status() -> None:
    result = OdinHealthcheck(log_root="logs").run()
    assert result["status"] in {"OK", "WARNING", "BLOCKED"}
    assert "network" in result["checks"]
