from __future__ import annotations

from dataclasses import dataclass


READ_INTENTS = {
    "Qual é o estado do ODIN?": "read_status",
    "O ODIN pode operar agora?": "read_can_operate",
    "Quais são os sinais activos?": "read_signals",
    "Qual é o estado do risco?": "read_risk",
    "O MT5 está ligado?": "read_mt5",
    "Que posições estão abertas no MT5?": "read_mt5_positions",
    "O ODIN reconhece todas as posições?": "read_mt5_reconciliation",
    "Há posições sem stop loss?": "read_mt5_unprotected",
    "Há posições externas ao ODIN?": "read_mt5_external",
    "O MT5 está seguro para operar em sombra?": "read_mt5_safety",
    "Qual foi a última reconciliação MT5?": "read_mt5_reconciliation_last",
    "Qual é o estado do ATLAS?": "read_atlas",
    "O que diz o ATLAS sobre o último sinal?": "read_atlas_last_signal",
    "Há notícias financeiras relevantes?": "read_news",
    "Qual é o estado FIRE?": "read_fire",
    "Mostra os últimos erros.": "read_errors",
    "Mostra os últimos sinais bloqueados.": "read_blocked_signals",
    "Qual é o estado runtime do ODIN?": "read_runtime_status",
    "O ODIN está vivo?": "read_runtime_alive",
    "Quando foi o último heartbeat?": "read_runtime_heartbeat",
    "O runtime está bloqueado?": "read_runtime_blocked",
    "Porque o runtime está em BLOCKED?": "read_runtime_blocked_reason",
    "Mostra o snapshot actual.": "read_runtime_snapshot",
    "Mostra os últimos eventos.": "read_runtime_events",
    "O ODIN pode continuar em sombra?": "read_runtime_shadow",
    "O sistema está pronto para soak test?": "read_runtime_soak",
    "O ODIN está estável?": "read_runtime_stable",
    "Qual foi o último soak test?": "read_runtime_soak_latest",
    "O heartbeat está actualizado?": "read_runtime_heartbeat",
    "O snapshot está válido?": "read_runtime_validate",
    "Houve erros no runtime?": "read_runtime_events",
    "Houve alguma tentativa de ordem?": "read_runtime_soak_safety",
    "O ODIN está pronto para um soak test longo?": "read_runtime_soak_long",
    "O ODIN está pronto para correr em sombra durante várias horas?": "read_runtime_soak_long",
}

COMMAND_INTENTS = {
    "Executa healthcheck.": "RUN_HEALTHCHECK",
    "Sincroniza posições MT5.": "SYNC_MT5_POSITIONS",
    "Pausa o ODIN.": "PAUSE_ODIN",
    "Retoma o ODIN.": "RESUME_ODIN",
}

DANGEROUS_PATTERNS = (
    "activa trading real",
    "ativa trading real",
    "enable real trading",
    "order_send",
    "enviar ordem",
    "fecha posição",
    "fechar posição",
    "desliga risk engine",
    "disable risk engine",
    "apaga logs",
    "delete logs",
)

SCOPE_HINTS = (
    "odin",
    "mt5",
    "atlas",
    "risco",
    "risk",
    "broker",
    "fire",
    "healthcheck",
    "notícias",
    "news",
    "sinal",
    "logs",
    "telegram",
    "dashboard",
    "runtime",
    "heartbeat",
    "snapshot",
    "evento",
    "event",
    "soak",
)


@dataclass(slots=True)
class IntentResult:
    intent_type: str
    intent_name: str


class IntentClassifier:
    def classify(self, question: str) -> IntentResult:
        text = question.strip()
        low = text.lower()

        if text in COMMAND_INTENTS:
            return IntentResult("command", COMMAND_INTENTS[text])
        if text in READ_INTENTS:
            return IntentResult("read", READ_INTENTS[text])

        if any(pattern in low for pattern in DANGEROUS_PATTERNS):
            return IntentResult("dangerous", "dangerous_command_blocked")

        if any(hint in low for hint in SCOPE_HINTS):
            if "healthcheck" in low:
                return IntentResult("command", "RUN_HEALTHCHECK")
            return IntentResult("read", "read_free")

        return IntentResult("out_of_scope", "out_of_scope")
