"""Explicit contracts for the supervised MT5 DEMO execution boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TradeProposal:
    proposal_id: str
    decision_id: str
    timestamp_utc: str
    symbol: str
    side: str
    volume: float
    entry_reference: float
    stop_loss: float
    take_profit: float
    strategy_id: str
    strategy_version: str
    reason_codes: tuple[str, ...]
    market_data_hash: str
    data_quality: str
    freshness: str
    expiry: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DemoRiskLimits:
    max_risk_per_trade: float = 10.0
    max_daily_demo_loss: float = 50.0
    max_drawdown_percent: float = 5.0
    max_position_size: float = 0.01
    max_simultaneous_positions: int = 1
    max_simultaneous_orders: int = 1
    minimum_free_margin: float = 1_000.0
    max_spread: float = 0.00030
    stale_data_threshold_seconds: int = 60
    maximum_order_retries: int = 1
    maximum_execution_slippage_points: int = 20

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DemoAccountEvidence:
    expected_terminal_path: str
    terminal_path: str
    expected_broker: str
    broker: str
    expected_server: str
    server: str
    expected_login: str
    login: str
    account_mode: str
    terminal_connected: bool
    terminal_trade_allowed: bool
    market_open: bool
    symbol: str
    data_fresh: bool
    data_age_seconds: int
    reconciliation_status: str
    kill_switch_engaged: bool
    open_positions: int
    active_orders: int
    free_margin: float
    daily_realized_pnl: float
    drawdown_percent: float
    spread: float
    volume_min: float
    volume_max: float
    volume_step: float
    point: float
    digits: int
    stops_level_points: int
    trade_tick_size: float
    trade_tick_value_loss: float
    fallback_used: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CanaryAuthorization:
    proposal_id: str
    account_fingerprint: str
    issued_at_utc: str
    expires_at_utc: str
    single_use: bool
    consumed: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
