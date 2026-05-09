from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from odin_assistant.context_builder import ContextBuilder
from odin_assistant.intent_classifier import IntentClassifier
from odin_assistant.local_llm_interface import LocalLLMInterface
from odin_assistant.permissions import AssistantPermissionGuard
from odin_assistant.question_registry import QuestionRegistry
from odin_assistant.redaction import redact_for_assistant
from odin_assistant.response_formatter import ResponseFormatter, SAFE_FALLBACK
from odin_control.system_controller import SystemController
from odin_logs.logger import JsonlLogger
from odin_logs.schemas import make_id


READ_MAP = {
    "read_status": "status",
    "read_can_operate": "can_operate",
    "read_signals": "signals",
    "read_risk": "risk",
    "read_mt5": "mt5",
    "read_mt5_positions": "mt5_positions",
    "read_mt5_reconciliation": "mt5_reconciliation",
    "read_atlas": "atlas",
    "read_atlas_last_signal": "atlas",
    "read_news": "news",
    "read_fire": "fire",
    "read_errors": "last_error",
    "read_blocked_signals": "blocked_signals",
    "read_mt5_unprotected": "mt5_reconciliation",
    "read_mt5_external": "mt5_reconciliation",
    "read_mt5_safety": "mt5_health",
    "read_mt5_reconciliation_last": "mt5_reconciliation",
    "read_free": "full_context",
}

MT5_UNAVAILABLE_MSG = (
    "MT5 indisponível neste ambiente. O ODIN está bloqueado para trading e continua disponível para diagnóstico."
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
        self.context_builder = context_builder or ContextBuilder.from_controller(controller, log_root=log_root)
        self.llm = LocalLLMInterface()

        self.allow_free_text = os.getenv("ODIN_ASSISTANT_ALLOW_FREE_TEXT", "true").lower() == "true"
        self.block_out_of_scope = os.getenv("ODIN_ASSISTANT_BLOCK_OUT_OF_SCOPE", "true").lower() == "true"

        self.dashboard_log = JsonlLogger(root / "assistant" / "dashboard_questions.log")
        self.telegram_log = JsonlLogger(root / "assistant" / "telegram_questions.log")
        self.llm_prompts_log = JsonlLogger(root / "assistant" / "llm_prompts.log")
        self.llm_log = JsonlLogger(root / "assistant" / "llm_responses.log")
        self.blocked_log = JsonlLogger(root / "assistant" / "blocked_requests.log")
        self.command_log = JsonlLogger(root / "assistant" / "command_requests.log")
        self.context_log = JsonlLogger(root / "assistant" / "context_used.log")

    def _security_state(self) -> str:
        trading_real_blocked = os.getenv("ENABLE_REAL_TRADING", "false").lower() != "true"
        broker_real_blocked = os.getenv("BROKER_ALLOW_REAL_EXECUTION", "false").lower() != "true"
        mt5_send_blocked = os.getenv("MT5_ORDER_SEND_ENABLED", "false").lower() != "true"
        if trading_real_blocked and broker_real_blocked and mt5_send_blocked:
            return "safe_guards_active"
        return "safety_misaligned"

    def _log_question(self, *, channel: str, question_id: str, question: str) -> None:
        data = {
            "question_id": question_id,
            "question": redact_for_assistant(question),
            "source": channel,
        }
        if channel == "telegram":
            self.telegram_log.write("telegram_question", data)
        else:
            self.dashboard_log.write("dashboard_question", data)

    def _is_mt5_unavailable(self, payload: dict[str, Any]) -> bool:
        text = str(payload).lower()
        return "metatrader5" in text and ("indispon" in text or "unavailable" in text)

    def _response(
        self,
        *,
        answer: str,
        source: str,
        context_used: bool,
        has_sufficient_data: bool,
        status: str,
        fallback_used: bool,
        question_id: str,
    ) -> dict[str, Any]:
        payload = self.formatter.build_response(
            answer=answer,
            source=source,
            context_used=context_used,
            has_sufficient_data=has_sufficient_data,
            security_state=self._security_state(),
            status=status,
            fallback_used=fallback_used,
        )
        payload["question_id"] = question_id
        payload["llm_enabled"] = self.llm.is_enabled()
        payload["ok"] = status in {"OK", "WARNING"}
        return payload

    def ask(self, question: str, *, channel: str = "dashboard", confirmed: bool = False) -> dict[str, Any]:
        question_id = make_id("q")
        question = question.strip()
        self._log_question(channel=channel, question_id=question_id, question=question)

        known_question = self.registry.is_allowed(question)
        intent = self.classifier.classify(question)

        if intent.intent_type == "dangerous":
            self.blocked_log.write(
                "blocked_request",
                {
                    "question_id": question_id,
                    "channel": channel,
                    "question": redact_for_assistant(question),
                    "reason": "dangerous_command_blocked",
                },
            )
            return self._response(
                answer=self.formatter.format_error("dangerous_command_blocked"),
                source="fallback",
                context_used=False,
                has_sufficient_data=False,
                status="BLOCKED",
                fallback_used=True,
                question_id=question_id,
            )

        if intent.intent_type == "out_of_scope" and self.block_out_of_scope:
            self.blocked_log.write(
                "blocked_request",
                {
                    "question_id": question_id,
                    "channel": channel,
                    "question": redact_for_assistant(question),
                    "reason": "out_of_scope",
                },
            )
            return self._response(
                answer=self.formatter.format_error("pergunta fora de escopo"),
                source="fallback",
                context_used=False,
                has_sufficient_data=False,
                status="BLOCKED",
                fallback_used=True,
                question_id=question_id,
            )

        if not known_question and not self.allow_free_text:
            self.blocked_log.write(
                "blocked_request",
                {
                    "question_id": question_id,
                    "channel": channel,
                    "question": redact_for_assistant(question),
                    "reason": "out_of_registry",
                },
            )
            return self._response(
                answer=self.formatter.format_error("pergunta fora de escopo"),
                source="fallback",
                context_used=False,
                has_sufficient_data=False,
                status="BLOCKED",
                fallback_used=True,
                question_id=question_id,
            )

        if intent.intent_type == "read":
            full_context = self.context_builder.build_for_question(question).payload
            self.context_log.write(
                "assistant_context",
                {
                    "question_id": question_id,
                    "intent": intent.intent_name,
                    "channel": channel,
                    "context": full_context,
                },
            )
            key = READ_MAP.get(intent.intent_name, "full_context")
            payload = full_context if key == "full_context" else full_context.get(key)
            payload_dict = payload if isinstance(payload, dict) else {"value": payload}

            if self._is_mt5_unavailable(payload_dict):
                return self._response(
                    answer=MT5_UNAVAILABLE_MSG,
                    source="fallback",
                    context_used=True,
                    has_sufficient_data=True,
                    status="WARNING",
                    fallback_used=True,
                    question_id=question_id,
                )

            prompt = (
                "Responde de forma curta, técnica e accionável com base no contexto ODIN. "
                "Se faltarem dados responde exactamente: Não existem dados suficientes para responder com segurança."
            )
            self.llm_prompts_log.write(
                "llm_prompt",
                {
                    "question_id": question_id,
                    "channel": channel,
                    "question": redact_for_assistant(question),
                    "prompt": redact_for_assistant(prompt),
                    "source": channel,
                    "provider": self.llm.runtime.provider,
                    "model": self.llm.runtime.model,
                    "context": payload_dict,
                },
            )
            llm_result = self.llm.safe_answer(question, payload_dict)
            self.llm_log.write(
                "llm_response",
                {
                    "question_id": question_id,
                    "channel": channel,
                    "source": channel,
                    "provider": llm_result.get("provider"),
                    "model": llm_result.get("model"),
                    "status": llm_result.get("status"),
                    "error": redact_for_assistant(llm_result.get("error")),
                    "latency_ms": llm_result.get("latency_ms"),
                    "used_context": llm_result.get("used_context"),
                    "safe": llm_result.get("safe"),
                    "response": redact_for_assistant(llm_result.get("response", "")),
                },
            )

            if llm_result.get("status") == "OK" and str(llm_result.get("response", "")).strip():
                return self._response(
                    answer=str(llm_result.get("response", "")).strip(),
                    source="local_llm",
                    context_used=bool(llm_result.get("used_context", True)),
                    has_sufficient_data=True,
                    status="OK",
                    fallback_used=False,
                    question_id=question_id,
                )

            fallback_answer = self.formatter.format_read(payload_dict)
            if not payload_dict:
                fallback_answer = SAFE_FALLBACK
            return self._response(
                answer=fallback_answer,
                source="fallback",
                context_used=True,
                has_sufficient_data=bool(payload_dict),
                status="WARNING",
                fallback_used=True,
                question_id=question_id,
            )

        if intent.intent_type != "command":
            return self._response(
                answer=SAFE_FALLBACK,
                source="fallback",
                context_used=False,
                has_sufficient_data=False,
                status="WARNING",
                fallback_used=True,
                question_id=question_id,
            )

        permission = self.permissions.check(intent.intent_name)
        if not permission.allowed:
            self.blocked_log.write(
                "blocked_command",
                {
                    "question_id": question_id,
                    "question": redact_for_assistant(question),
                    "command": intent.intent_name,
                    "reason": permission.reason,
                },
            )
            return self._response(
                answer=self.formatter.format_error(permission.reason),
                source="fallback",
                context_used=False,
                has_sufficient_data=False,
                status="BLOCKED",
                fallback_used=True,
                question_id=question_id,
            )

        if permission.confirmation_required and not confirmed:
            return self._response(
                answer="Confirmação necessária.",
                source="command_bus",
                context_used=False,
                has_sufficient_data=True,
                status="WARNING",
                fallback_used=False,
                question_id=question_id,
            )

        self.command_log.write(
            "assistant_command",
            {
                "question_id": question_id,
                "command": intent.intent_name,
                "channel": channel,
                "source": channel,
                "confirmed": confirmed,
            },
        )
        cmd_result = self.controller.execute(intent.intent_name, actor=f"assistant:{channel}", role="assistant")
        accepted = bool(cmd_result.get("accepted", False))
        return self._response(
            answer=str(cmd_result),
            source="command_bus",
            context_used=False,
            has_sufficient_data=True,
            status="OK" if accepted else "WARNING",
            fallback_used=False,
            question_id=question_id,
        )

    def llm_status(self) -> dict[str, Any]:
        return self.llm.healthcheck()
