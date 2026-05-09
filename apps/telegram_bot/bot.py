from __future__ import annotations

import os
from dataclasses import dataclass

from odin_assistant.assistant_router import AssistantRouter
from odin_control.system_controller import SystemController
from odin_logs.logger import JsonlLogger


COMMAND_TO_QUESTION = {
    "/status": "Qual é o estado do ODIN?",
    "/can_trade": "O ODIN pode operar agora?",
    "/signals": "Quais são os sinais activos?",
    "/risk": "Qual é o estado do risco?",
    "/mt5": "O MT5 está ligado?",
    "/atlas": "Qual é o estado do ATLAS?",
    "/atlas_status": "Qual é o estado do ATLAS?",
    "/atlas_last": "O que diz o ATLAS sobre o último sinal?",
    "/fire": "Qual é o estado FIRE?",
    "/logs": "Mostra os últimos erros.",
    "/healthcheck": "Executa healthcheck.",
    "/pause": "Pausa o ODIN.",
    "/resume": "Retoma o ODIN.",
    "/sync_mt5": "Sincroniza posições MT5.",
}


@dataclass(slots=True)
class TelegramMessage:
    user_id: str
    text: str
    confirmed: bool = False


class TelegramBot:
    def __init__(self, controller: SystemController) -> None:
        self.controller = controller
        self.assistant = AssistantRouter(controller)
        self.log_messages = JsonlLogger("logs/telegram/messages.log")
        self.log_approvals = JsonlLogger("logs/telegram/approvals.log")
        allowed_raw = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        self.allowed_ids = {x.strip() for x in allowed_raw.split(",") if x.strip()}

    def is_allowed(self, user_id: str) -> bool:
        return user_id in self.allowed_ids if self.allowed_ids else False

    def handle(self, message: TelegramMessage) -> dict[str, object]:
        self.log_messages.write("telegram_message", {"user_id": message.user_id, "text": message.text})

        if not self.is_allowed(message.user_id):
            return {"ok": False, "answer": "Utilizador não autorizado."}

        if message.text == "/help":
            return {"ok": True, "answer": "Comandos: " + ", ".join(sorted(list(COMMAND_TO_QUESTION.keys()) + ["/help"]))}

        question = COMMAND_TO_QUESTION.get(message.text)
        if not question:
            return {"ok": False, "answer": "Comando não suportado."}

        if message.confirmed:
            self.log_approvals.write("telegram_command_confirmed", {"user_id": message.user_id, "text": message.text})

        return self.assistant.ask(question, channel="telegram", confirmed=message.confirmed)


def main() -> None:
    controller = SystemController(log_root="logs")
    bot = TelegramBot(controller)
    print("Telegram bot structure ready. Configure polling/webhook externally.")
    print(bot.handle(TelegramMessage(user_id="0", text="/help")))


if __name__ == "__main__":
    main()
