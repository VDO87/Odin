"""Deterministic replay account for visual DEMO learning, never execution."""

from __future__ import annotations

from odin.data.candles import candles_for
from odin.data.public_observation import public_observation_cache_status
from odin.trading.replay_config import load_replay_config
from odin.adapters.mt5.demo_readonly_state import read_demo_readonly_state


def replay_trading_state(symbol: str = "EURUSD", timeframe: str = "M15") -> dict[str, object]:
    """Return a fixed simulated account and market snapshot for the TradeDesk."""
    candles = [candle.to_dict() for candle in candles_for(symbol, timeframe)]
    public_data = public_observation_cache_status("/mnt/d/ODIN_LOCAL/cache/public")
    configuration = load_replay_config()
    mt5_demo = read_demo_readonly_state()
    positions = [
        {"ticket": "R-1001", "symbol": "EURUSD", "side": "BUY", "volume": 0.05,
         "entry": 1.0842, "mark": 1.0850, "stop_loss": 1.0815, "take_profit": 1.0895,
         "profit": 4.0, "risk_to_stop": 13.5, "mode": "REPLAY"},
    ]
    orders = [
        {"ticket": "R-0998", "symbol": "EURUSD", "side": "SELL", "status": "CLOSED",
         "opened_at": "2026-07-30T10:00:00+00:00", "closed_at": "2026-07-30T14:15:00+00:00",
         "profit": 7.5, "mode": "REPLAY"},
        {"ticket": "R-0997", "symbol": "EURUSD", "side": "BUY", "status": "CLOSED",
         "opened_at": "2026-07-29T09:45:00+00:00", "closed_at": "2026-07-29T12:30:00+00:00",
         "profit": -3.0, "mode": "REPLAY"},
    ]
    journal = [{"id": "J-1001", "symbol": "EURUSD", "state": "OPEN_REPLAY", "context": "trend_retest", "entry": 1.0842, "stop_loss": 1.0815, "take_profit": 1.0895, "risk": 13.5, "reason": "replay_price_above_local_average", "outcome": "awaiting_close"}, {"id": "J-0998", "symbol": "EURUSD", "state": "CLOSED_REPLAY", "context": "range_break", "entry": 1.0861, "stop_loss": 1.0880, "take_profit": 1.0820, "risk": 9.5, "reason": "replay_break_below_range", "outcome": "profit_7.50"}]
    metrics = replay_metrics(orders)
    balance = 10_000.0
    open_profit = sum(float(position["profit"]) for position in positions)
    equity = balance + open_profit
    return {
        "status": "OK", "component": "trading_replay", "mode": "DEMO_REPLAY",
        "account": {"name": "ODIN Replay Account", "currency": "EUR", "balance": balance,
                    "equity": equity, "free_margin": 9_750.0, "used_margin": 250.0,
                    "daily_profit": 8.5, "drawdown_percent": 0.3, "account_connected": False},
        "market": {"symbol": symbol, "timeframe": timeframe, "bid": 1.08500, "ask": 1.08508,
                   "spread": 0.00008, "candles": candles, "data_source": "local_replay"},
        "public_data": public_data,
        "positions": positions, "orders": orders, "metrics": metrics, "decision_journal": journal,
        "risk": {"open_exposure": 0.05, "risk_to_stops": 13.5,
                 "daily_loss_limit": configuration["risk_limits"]["daily_loss_limit"],
                 "per_trade_risk_limit": configuration["risk_limits"]["per_trade_risk_limit"],
                 "max_position_lots": configuration["risk_limits"]["max_position_lots"],
                 "kill_switch_engaged": False},
        "configuration": configuration,
        "mt5_demo": mt5_demo,
        "odin": {"state": "OBSERVING", "next_action": "collect_replay_outcome",
                 "reason": "replay_only_no_broker_connection"},
        "execution_allowed": False, "safe_to_trade": False, "real_trading": False,
    }


def replay_metrics(orders: list[dict[str, object]]) -> dict[str, object]:
    """Calculate visible replay outcome metrics; values are not investment advice."""
    closed = [item for item in orders if item.get("status") == "CLOSED"]
    gross = sum(float(item.get("profit", 0.0)) for item in closed)
    costs = 1.2
    wins = sum(1 for item in closed if float(item.get("profit", 0.0)) > 0)
    losses = len(closed) - wins
    peak = 0.0
    running = 0.0
    max_drawdown = 0.0
    for item in closed:
        running += float(item.get("profit", 0.0))
        peak = max(peak, running)
        max_drawdown = max(max_drawdown, peak - running)
    return {
        "closed_count": len(closed), "wins": wins, "losses": losses,
        "win_rate_percent": round(wins / len(closed) * 100, 1) if closed else 0.0,
        "gross_profit": round(gross, 2), "costs": costs, "net_profit": round(gross - costs, 2),
        "max_replay_drawdown": round(max_drawdown, 2), "simulated": True,
    }
