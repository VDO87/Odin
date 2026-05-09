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
    "Qual é o estado do ATLAS?": "read_atlas",
    "O que diz o ATLAS sobre o último sinal?": "read_atlas_last_signal",
    "Há notícias financeiras relevantes?": "read_news",
    "Qual é o estado FIRE?": "read_fire",
    "Mostra os últimos erros.": "read_errors",
    "Mostra os últimos sinais bloqueados.": "read_blocked_signals",
    "Há posições sem stop loss?": "read_mt5_unprotected",
    "Há posições externas ao ODIN?": "read_mt5_external",
    "O MT5 está seguro para operar em sombra?": "read_mt5_safety",
    "Qual foi a última reconciliação MT5?": "read_mt5_reconciliation_last",
}

COMMAND_INTENTS = {
    "Executa healthcheck.": "RUN_HEALTHCHECK",
    "Sincroniza posições MT5.": "SYNC_MT5_POSITIONS",
    "Pausa o ODIN.": "PAUSE_ODIN",
    "Retoma o ODIN.": "RESUME_ODIN",
}


@dataclass(slots=True)
class IntentResult:
    intent_type: str
    intent_name: str


class IntentClassifier:
    def classify(self, question: str) -> IntentResult:
        text = question.strip()
        if text in COMMAND_INTENTS:
            return IntentResult("command", COMMAND_INTENTS[text])
        if text in READ_INTENTS:
            return IntentResult("read", READ_INTENTS[text])
        return IntentResult("unknown", "unknown")
