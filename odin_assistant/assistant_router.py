from __future__ import annotations

from pathlib import Path
from typing import Any

from odin_assistant.context_builder import ContextBuilder
from odin_assistant.intent_classifier import IntentClassifier
from odin_assistant.permissions import AssistantPermissionGuard
from odin_assistant.question_registry import QuestionRegistry
from odin_assistant.response_formatter import ResponseFormatter, SAFE_FALLBACK
from odin_control.system_controller import SystemController
from odin_logs.logger import JsonlLogger


READ_MAP = {
    "read_status": "status",
    "read_can_operate": "can_operate",
    "read_signals": "signals",
    "read_risk": "risk",
    "read_mt5": "mt5",
    "read_mt5_positions": "mt5_positions",
    "read_mt5_reconciliation": "mt5_reconciliation",
    "read_atlas": "atlas",
    "read_atlas_last_signal": "atlas_last_signal",
    "read_news": "news",
    "read_fire": "fire",
    "read_errors": "errors",
    "read_blocked_signals": "blocked_signals",
    "read_mt5_unprotected": "mt5_unprotected",
    "read_mt5_external": "mt5_external",
    "read_mt5_safety": "mt5_safety",
    "read_mt5_reconciliation_last": "mt5_reconciliation_last",
}

MT5_UNAVAILABLE_MSG = (
    "MT5 indisponível neste ambiente. O ODIN está bloqueado para trading e continua disponível para diagnóstico."
)


def _default_context_builder(controller: SystemController) -> ContextBuilder:
    return ContextBuilder(
        {
            "status": lambda: {"state": controller.machine.state.value},
            "can_operate": lambda: {"can_operate": controller.machine.state.value in {"READY", "RUNNING"}},
            "signals": lambda: {"active_signals": []},
            "risk": lambda: {"risk_engine_required": True, "risk_engine_active": True},
            "mt5": lambda: controller.execute("MT5_STATUS", actor="assistant", role="assistant"),
            "mt5_positions": lambda: controller.execute("MT5_LIST_POSITIONS", actor="assistant", role="assistant"),
            "mt5_reconciliation": lambda: controller.execute("MT5_SYNC_POSITIONS", actor="assistant", role="assistant"),
            "mt5_safety": lambda: controller.execute("MT5_HEALTHCHECK", actor="assistant", role="assistant"),
            "mt5_reconciliation_last": lambda: controller.execute("MT5_SYNC_POSITIONS", actor="assistant", role="assistant"),
            "mt5_unprotected": lambda: controller.execute("MT5_SYNC_POSITIONS", actor="assistant", role="assistant"),
            "mt5_external": lambda: controller.execute("MT5_SYNC_POSITIONS", actor="assistant", role="assistant"),
            "atlas": lambda: {"status": "enabled_consensus_only"},
            "atlas_last_signal": lambda: {"status": "no_signals"},
            "news": lambda: {"status": "not_configured"},
            "fire": lambda: {"status": "monitoring"},
            "errors": lambda: {"last_errors": []},
            "blocked_signals": lambda: {"last_blocked": []},
        }
    )


class AssistantRouter:
    def __init__(
        self,
        controller: SystemController,
        *,
        registry_path: str | Path = "config/question_registry.yaml",
        log_root: str | Path = "logs",
        context_builder: ContextBuilder | None = None,
    ) -> None:
        root = Path(log_root)
        self.controller = controller
        self.registry = QuestionRegistry(registry_path)
        self.classifier = IntentClassifier()
        self.permissions = AssistantPermissionGuard()
        self.formatter = ResponseFormatter()
        self.context_builder = context_builder or _default_context_builder(controller)

        self.dashboard_log = JsonlLogger(root / "assistant" / "dashboard_questions.log")
        self.telegram_log = JsonlLogger(root / "assistant" / "telegram_questions.log")
        self.llm_log = JsonlLogger(root / "assistant" / "llm_responses.log")
        self.blocked_log = JsonlLogger(root / "assistant" / "blocked_requests.log")
        self.command_log = JsonlLogger(root / "assistant" / "command_requests.log")
        self.context_log = JsonlLogger(root / "assistant" / "context_used.log")

    def ask(self, question: str, *, channel: str = "dashboard", confirmed: bool = False) -> dict[str, Any]:
        question = question.strip()
        if channel == "telegram":
            self.telegram_log.write("telegram_question", {"question": question})
        else:
            self.dashboard_log.write("dashboard_question", {"question": question})

        if not self.registry.is_allowed(question):
            self.blocked_log.write("blocked_question", {"question": question, "reason": "out_of_registry"})
            return {"ok": False, "answer": self.formatter.format_error("pergunta fora de escopo")}

        intent = self.classifier.classify(question)
        if intent.intent_type == "unknown":
            return {"ok": False, "answer": SAFE_FALLBACK}

        if intent.intent_type == "read":
            ctx = self.context_builder.build().payload
            self.context_log.write("assistant_context", {"context": ctx, "intent": intent.intent_name})
            key = READ_MAP[intent.intent_name]
            answer_payload = ctx.get(key)
            if answer_payload is None:
                return {"ok": False, "answer": SAFE_FALLBACK}
            if key.startswith("mt5"):
                payload_text = str(answer_payload).lower()
                if "indisponível" in payload_text or "unavailable" in payload_text:
                    return {"ok": False, "answer": MT5_UNAVAILABLE_MSG}
                if isinstance(answer_payload, dict):
                    mt5_data = answer_payload.get("data", {}).get("mt5")
                    if isinstance(mt5_data, dict) and mt5_data.get("status") in {"WARNING", "BLOCKED"}:
                        message = str(mt5_data.get("message", "")).lower()
                        if "indisponível" in message or "unavailable" in message:
                            return {"ok": False, "answer": MT5_UNAVAILABLE_MSG}
            return {"ok": True, "answer": self.formatter.format_read(answer_payload)}

        permission = self.permissions.check(intent.intent_name)
        if not permission.allowed:
            self.blocked_log.write(
                "blocked_command",
                {"question": question, "command": intent.intent_name, "reason": permission.reason},
            )
            return {"ok": False, "answer": self.formatter.format_error(permission.reason)}

        if permission.confirmation_required and not confirmed:
            return {"ok": False, "confirmation_required": True, "answer": "Confirmação necessária."}

        self.command_log.write("assistant_command", {"command": intent.intent_name, "channel": channel})
        cmd_result = self.controller.execute(intent.intent_name, actor=f"assistant:{channel}", role="assistant")
        return {"ok": bool(cmd_result.get("accepted", False)), "answer": str(cmd_result)}
