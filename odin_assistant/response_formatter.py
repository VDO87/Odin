from __future__ import annotations

from typing import Any


SAFE_FALLBACK = "Não existem dados suficientes para responder com segurança."


class ResponseFormatter:
    def format_read(self, payload: dict[str, Any]) -> str:
        if not payload:
            return SAFE_FALLBACK
        return str(payload)

    def format_error(self, reason: str) -> str:
        return f"Pedido bloqueado: {reason}"
