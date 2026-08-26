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
    assert '"broker_timestamp_raw"' in probe
    assert '"normalized_event_time_utc"' in probe
    assert '"normalization_method"' in probe
    assert "order_send" not in probe
    assert '"real_trading": False' in probe
    assert '"execution_allowed": False' in probe
    assert '"canary_confirmation_required": True' in probe
    assert '"login_mismatch"' in probe
    assert '"terminal_path_mismatch"' in probe


def test_stage0_control_is_permanently_disarmed_in_repo() -> None:
    control = (ROOT / "config/demo_execution_rc1.json").read_text(encoding="utf-8")
    assert '"canary_authorized": false' in control
    assert '"allowed_symbol": "EURUSD"' in control
    assert '"broker_symbol": "EURUSD.pro"' in control
    assert '"safe_to_trade": false' in control
    assert '"real_trading": false' in control
    assert '"execution_allowed": false' in control


def test_live_soak_preflight_is_read_only_and_uses_exact_oanda_terminal() -> None:
    launcher = (
        ROOT / "scripts/windows/Invoke-ODIN-MT5-Demo-Live-Soak-Preflight.ps1"
    ).read_text(encoding="utf-8")
    probe = (ROOT / "scripts/windows/mt5_demo_live_soak_preflight.py").read_text(
        encoding="utf-8"
    )
    assert r"C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe" in launcher
    assert "ODIN_OANDA_ACCOUNT_MODE" in launcher
    assert "ODIN_OANDA_LOGIN" in launcher
    assert "ODIN_OANDA_SERVER" in launcher
    assert "ODIN_OANDA_PASSWORD" not in launcher
    assert "run_bounded_precanary_soak" in probe
    assert "mt5.initialize" in probe
    assert "mt5.account_info" in probe
    assert "mt5.terminal_info" in probe
    assert "mt5.symbol_info" in probe
    assert "mt5.symbol_info_tick" in probe
    assert "mt5.positions_get" in probe
    assert "mt5.orders_get" in probe
    assert "mt5.shutdown" in probe
    assert 'BROKER_SYMBOL = "EURUSD.pro"' in probe
    assert "order_send" not in probe
    assert "order_check" not in probe
    assert '"broker_submission_called": False' in probe
