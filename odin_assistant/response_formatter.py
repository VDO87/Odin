from __future__ import annotations

from typing import Any


SAFE_FALLBACK = "Não existem dados suficientes para responder com segurança."


class ResponseFormatter:
    def format_read(self, payload: dict[str, Any] | None) -> str:
        if not payload:
            return SAFE_FALLBACK
        return str(payload)

    def format_error(self, reason: str) -> str:
        return f"Pedido bloqueado: {reason}"

    def build_response(
        self,
        *,
        answer: str,
        source: str,
        context_used: bool,
        has_sufficient_data: bool,
        security_state: str,
        status: str = "OK",
        fallback_used: bool = False,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "answer": answer,
            "source": source,
            "context_used": context_used,
            "has_sufficient_data": has_sufficient_data,
            "security_state": security_state,
            "fallback_used": fallback_used,
        }
