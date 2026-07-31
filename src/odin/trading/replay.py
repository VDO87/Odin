"""Deterministic replay account for visual DEMO learning, never execution."""

from __future__ import annotations

from odin.data.candles import candles_for


def replay_trading_state(symbol: str = "EURUSD", timeframe: str = "M15") -> dict[str, object]:
    """Return a fixed simulated account and market snapshot for the TradeDesk."""
    candles = [candle.to_dict() for candle in candles_for(symbol, timeframe)]
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
        "positions": positions, "orders": orders,
        "risk": {"open_exposure": 0.05, "risk_to_stops": 13.5, "daily_loss_limit": 100.0,
                 "kill_switch_engaged": False},
        "odin": {"state": "OBSERVING", "next_action": "collect_replay_outcome",
                 "reason": "replay_only_no_broker_connection"},
        "execution_allowed": False, "safe_to_trade": False, "real_trading": False,
    }
