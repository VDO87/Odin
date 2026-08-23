from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_stage0_launcher_uses_existing_identity_without_secret_output() -> None:
    launcher = (ROOT / "scripts/windows/Invoke-ODIN-MT5-Demo-DryRun.ps1").read_text(
        encoding="utf-8"
    )
    lowered = launcher.lower()
    assert "odin_oanda_account_mode" in lowered
    assert "odin_oanda_login" in lowered
    assert "odin_oanda_server" in lowered
    assert "odin_oanda_password" not in lowered
    assert "get-ciminstance" in lowered
    assert "order_send" not in lowered


def test_stage0_probe_is_dry_run_only_and_fail_closed() -> None:
    probe = (ROOT / "scripts/windows/mt5_demo_dry_run.py").read_text(encoding="utf-8")
    assert "run_demo_dry_run" in probe
    assert "mt5.initialize" in probe
    assert "mt5.account_info" in probe
    assert "mt5.positions_get" in probe
    assert "mt5.orders_get" in probe
    assert "mt5.history_deals_get" in probe
    assert "mt5.shutdown" in probe
    assert "assess_market_timestamp" in probe
    assert '"mt5_tick_time_raw"' in probe
    assert '"odin_now_utc"' in probe
    assert '"market_time_reason_codes"' in probe
    assert "order_send" not in probe
    assert '"real_trading": False' in probe
    assert '"execution_allowed": False' in probe
    assert '"canary_confirmation_required": True' in probe
    assert '"login_mismatch"' in probe
    assert '"terminal_path_mismatch"' in probe


def test_stage0_control_is_permanently_disarmed_in_repo() -> None:
    control = (ROOT / "config/demo_execution_rc1.json").read_text(encoding="utf-8")
    assert '"canary_authorized": false' in control
    assert '"safe_to_trade": false' in control
    assert '"real_trading": false' in control
    assert '"execution_allowed": false' in control
