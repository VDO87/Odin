from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_demo_state() -> dict[str, Any]:
    return {
        "demo_data": True,
        "timestamp": _now(),
        "version": "RC1.6-DEMO",
        "mode": "SHADOW_MT5",
        "runtime": {
            "state": "RUNNING",
            "safe_to_trade": False,
            "heartbeat": _now(),
            "health_status": "WARNING",
            "blocked_reasons": ["MT5 shadow only", "network diagnostic mode"],
            "uptime_seconds": 4321,
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
            "message": "MT5 indisponível (demo state)",
            "symbol": "EURUSD",
            "timeframe": "M15",
            "tick": {"bid": 1.08215, "ask": 1.08225, "spread": 10},
            "sparkline": [1.0818, 1.0820, 1.0822, 1.0821, 1.0823, 1.0822, 1.08215],
        },
        "atlas": {
            "status": "OK",
            "profile": "lite",
            "consensus": 0.68,
            "critic": "active",
            "execution_permission": "SHADOW_ONLY",
            "agents": {
                "market_agent": "OK",
                "technical_agent": "OK",
                "risk_agent": "OK",
                "critic_agent": "OK",
            },
        },
        "llm": {
            "status": "WARNING",
            "provider": "ollama",
            "model": "",
            "message": "Modelo não configurado, fallback activo.",
        },
        "risk": {
            "engine": "REQUIRED",
            "max_risk_per_trade_percent": 0.25,
            "max_daily_loss_percent": 1.0,
            "max_trades_per_day": 5,
            "blocked_reasons": ["shadow_mode_only"],
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
            "items": [],
        },
        "assistant": {
            "last_question": "Qual é o estado do ODIN?",
            "last_answer": "ODIN em shadow mode, trading real bloqueado.",
            "source": "fallback",
        },
        "news": [
            "DEMO DATA: Mercado em sessão regular.",
            "DEMO DATA: Volatilidade moderada em FX majors.",
        ],
        "events": [
            {"timestamp": _now(), "event_type": "HEARTBEAT", "message": "Runtime heartbeat ok"},
            {
                "timestamp": _now(),
                "event_type": "HEALTHCHECK_WARNING",
                "message": "Network/DNS parcial no ambiente",
            },
            {
                "timestamp": _now(),
                "event_type": "COMMAND_BLOCKED",
                "message": "ENABLE_REAL_TRADING bloqueado",
            },
        ],
        "errors": [],
        "soak": {
            "result": "PASS",
            "total_cycles": 12,
            "failed_cycles": 0,
            "no_order_attempts": True,
        },
    }
