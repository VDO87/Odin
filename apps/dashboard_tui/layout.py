from __future__ import annotations

from typing import Any

from odin_dashboard.formatters import short_ts
from apps.dashboard_tui.widgets import badge, kv, spark


def _headline(state: dict[str, Any]) -> str:
    runtime = state.get("runtime", {})
    security = state.get("security_badges", {})
    return " | ".join(
        [
            badge("ODIN", str(state.get("version", "RC1.6"))),
            badge("MODE", str(state.get("mode", "SHADOW_MT5"))),
            badge("RUNTIME", str(runtime.get("state", "UNKNOWN"))),
            badge("SAFE_TO_TRADE", str(runtime.get("safe_to_trade", False))),
            badge("TRADING REAL", str(security.get("TRADING REAL", "BLOCKED"))),
        ]
    )


def render_text_dashboard(state: dict[str, Any]) -> str:
    runtime = state.get("runtime", {})
    mt5 = state.get("mt5", {})
    atlas = state.get("atlas", {})
    llm = state.get("llm", {})
    risk = state.get("risk", {})
    positions = state.get("positions", {})
    assistant = state.get("assistant", {})
    events = state.get("events", [])
    blocked = state.get("blocked_commands", [])
    security = state.get("security_badges", {})

    mt5_tick = mt5.get("tick", {})
    if not mt5_tick and isinstance(mt5.get("raw"), dict):
        mt5_tick = (
            mt5.get("raw", {})
            .get("data", {})
            .get("mt5", {})
            .get("data", {})
            .get("tick", {})
        )
    curve = mt5.get("sparkline", [])

    lines: list[str] = []
    lines.append("=" * 110)
    lines.append(_headline(state))
    lines.append("=" * 110)
    lines.append("SYSTEM")
    lines.append(kv("Heartbeat", short_ts(runtime.get("heartbeat"))))
    lines.append(kv("Health", runtime.get("health_status", "UNKNOWN")))
    lines.append(kv("Runtime", runtime.get("state", "UNKNOWN")))
    lines.append(kv("Demo data", state.get("demo_data", False)))
    lines.append("")

    lines.append("MARKET / MT5")
    lines.append(kv("MT5 status", mt5.get("status", "UNKNOWN")))
    lines.append(kv("Symbol", mt5.get("symbol", "EURUSD")))
    lines.append(kv("Timeframe", mt5.get("timeframe", "M15")))
    lines.append(kv("Bid", mt5_tick.get("bid", "n/a")))
    lines.append(kv("Ask", mt5_tick.get("ask", "n/a")))
    lines.append(kv("Spread", mt5_tick.get("spread", "n/a")))
    lines.append(kv("Chart", spark(curve) if curve else "n/a"))
    lines.append("")

    lines.append("ATLAS")
    lines.append(kv("Profile", atlas.get("profile", "lite")))
    lines.append(kv("Consensus", atlas.get("consensus", atlas.get("decision_packet", {}).get("consensus_score", "n/a"))))
    lines.append(kv("Critic", atlas.get("critic", atlas.get("critic_agent_result", "n/a"))))
    lines.append(kv("Execution", atlas.get("execution_permission", "SHADOW_ONLY")))
    lines.append("")

    lines.append("RISK")
    lines.append(kv("Risk Engine", "REQUIRED"))
    lines.append(kv("Max risk/trade", risk.get("max_risk_per_trade_percent", "0.25")))
    lines.append(kv("Max daily loss", risk.get("max_daily_loss_percent", "1.00")))
    lines.append(kv("Max trades/day", risk.get("max_trades_per_day", "5")))
    lines.append("")

    lines.append("POSITIONS")
    if isinstance(positions, dict):
        rec_source = positions.get("reconciliation", {})
        rec: dict[str, Any] = {}
        if isinstance(rec_source, dict):
            rec = rec_source.get("data", {}).get("reconciliation", {})
            if not isinstance(rec, dict):
                rec = {}
        lines.append(kv("Total", rec.get("total_positions", positions.get("total", 0))))
        lines.append(kv("External", rec.get("external_positions", positions.get("external", 0))))
        lines.append(kv("Unprotected", rec.get("unprotected_positions", positions.get("unprotected", 0))))
        lines.append(kv("Unknown magic", rec.get("unknown_magic", positions.get("unknown_magic", 0))))
        lines.append(kv("Reconciliation", rec.get("recommended_state", positions.get("reconciliation", "n/a"))))
    else:
        lines.append(kv("Total", "n/a"))
    lines.append("")

    lines.append("ASSISTANT")
    lines.append(kv("LLM status", llm.get("status", "UNKNOWN") if isinstance(llm, dict) else "UNKNOWN"))
    lines.append(kv("LLM provider", llm.get("provider", "n/a") if isinstance(llm, dict) else "n/a"))
    lines.append(kv("Last question", assistant.get("last_question", assistant.get("question", "n/a"))))
    lines.append(kv("Last answer", assistant.get("last_answer", assistant.get("answer", "n/a"))))
    lines.append(kv("Source", assistant.get("source", "n/a")))
    lines.append("")

    lines.append("SECURITY BADGES")
    for key, value in security.items():
        lines.append(kv(key, value))
    lines.append("")

    lines.append("LOGS / EVENTS")
    for item in events[-6:]:
        event_type = item.get("event_type") or item.get("data", {}).get("event_type", "EVENT")
        ts = item.get("timestamp") or item.get("data", {}).get("timestamp", "")
        lines.append(f"- {short_ts(ts)} {event_type}")
    if blocked:
        lines.append("BLOCKED COMMANDS")
        for item in blocked[-3:]:
            reason = item.get("data", {}).get("reason", "blocked")
            question = item.get("data", {}).get("question", "")
            lines.append(f"- {reason}: {question}")
    lines.append("")

    lines.append("COMMAND BAR")
    lines.append("status | pause | resume | healthcheck | sync MT5 | quit")
    lines.append("(dangerous commands are intentionally unavailable)")
    lines.append("=" * 110)
    return "\n".join(lines)
