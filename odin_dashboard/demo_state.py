from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_demo_state() -> dict[str, Any]:
    now = _now()
    return {
        "demo_data": True,
        "timestamp": now,
        "version": "RC1.6.1-DEMO",
        "mode": "SHADOW_MT5",
        "runtime": {
            "state": "RUNNING",
            "safe_to_trade": False,
            "heartbeat": now,
            "health_status": "WARNING",
            "blocked_reasons": ["MT5 shadow only", "network diagnostic mode"],
            "uptime_seconds": 12640,
            "runtime_validate": "PASS",
        },
        "security": {
            "trading_real_blocked": True,
            "mt5_order_send_blocked": True,
            "broker_real_blocked": True,
            "xtb_real_blocked": True,
            "atlas_execution": "SHADOW_ONLY",
            "llm_execution": "READ_ONLY",
        },
        "mt5": {
            "status": "BLOCKED",
            "message": "DEMO DATA: MT5 indisponível neste ambiente.",
            "symbol": "EURUSD",
            "timeframe": "M15",
            "tick": {"bid": 1.08218, "ask": 1.08230, "spread": 12},
            "sparkline": [
                1.08180,
                1.08192,
                1.08202,
                1.08212,
                1.08205,
                1.08221,
                1.08214,
                1.08226,
                1.08218,
            ],
            "chart_label": "DEMO DATA",
        },
        "market_intelligence": {
            "news_status": "DEMO",
            "macro_calendar_status": "DEMO",
            "sentiment_summary": "risk-neutral",
            "high_impact_events": [
                "US CPI (high impact) em 2h",
                "ECB member speech (medium impact)",
            ],
            "blocked_by_news": False,
        },
        "atlas": {
            "status": "OK",
            "profile": "lite",
            "consensus": 0.71,
            "critic": "active",
            "execution_permission": "SHADOW_ONLY",
            "agents": {
                "market_agent": "0.72",
                "technical_agent": "0.69",
                "news_agent": "0.63",
                "risk_agent": "ALLOW_SHADOW",
                "critic_agent": "PASS_WITH_CAUTION",
            },
        },
        "llm": {
            "status": "WARNING",
            "provider": "ollama",
            "model": "",
            "message": "Modelo não configurado, fallback activo.",
        },
        "risk": {
            "status": "ACTIVE",
            "engine": "REQUIRED",
            "max_risk_per_trade_percent": 0.25,
            "max_daily_loss_percent": 1.0,
            "max_trades_per_day": 5,
            "trades_today": 2,
            "consecutive_losses": 1,
            "blocked_reasons": ["shadow_mode_only"],
            "safe_to_trade": False,
        },
        "broker_router": {
            "enabled": True,
            "primary": "XTB",
            "allow_real_execution": False,
        },
        "positions": {
            "total": 0,
            "odin_managed": 0,
            "external": 0,
            "unprotected": 0,
            "unknown_magic": 0,
            "reconciliation": "READY",
            "recommended_state": "BLOCKED",
            "items": [],
        },
        "assistant": {
            "last_question": "O ODIN pode operar agora?",
            "last_answer": "Não. Modo SHADOW_MT5 com execução real bloqueada.",
            "source": "fallback",
        },
        "events": [
            {"timestamp": now, "event_type": "COMMAND_RECEIVED", "message": "RUNTIME_STATUS"},
            {"timestamp": now, "event_type": "COMMAND_RECEIVED", "message": "RUNTIME_STATUS"},
            {"timestamp": now, "event_type": "COMMAND_RECEIVED", "message": "RUNTIME_STATUS"},
            {"timestamp": now, "event_type": "HEARTBEAT", "message": "Runtime heartbeat ok"},
            {"timestamp": now, "event_type": "HEARTBEAT", "message": "Runtime heartbeat ok"},
            {"timestamp": now, "event_type": "HEARTBEAT", "message": "Runtime heartbeat ok"},
            {
                "timestamp": now,
                "event_type": "COMMAND_BLOCKED",
                "message": "ENABLE_REAL_TRADING blocked",
            },
            {
                "timestamp": now,
                "event_type": "ERROR",
                "message": "DNS unavailable in current environment",
            },
        ],
        "errors": [
            {
                "timestamp": now,
                "event_type": "ERROR",
                "message": "DEMO DATA: external API timeout",
            }
        ],
        "soak": {
            "result": "PASS",
            "total_cycles": 18,
            "failed_cycles": 0,
            "no_order_attempts": True,
        },
    }
