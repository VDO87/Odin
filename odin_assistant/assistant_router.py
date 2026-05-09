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
}


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
        self.context_builder = context_builder or ContextBuilder()

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
