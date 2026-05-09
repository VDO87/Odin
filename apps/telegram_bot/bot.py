from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from odin_assistant.assistant_router import AssistantRouter
from odin_control.system_controller import SystemController
from odin_core.runtime_validator import validate_runtime_artifacts
from odin_logs.logger import JsonlLogger


COMMAND_TO_QUESTION = {
    "/status": "Qual é o estado do ODIN?",
    "/odin": "Qual é o estado do ODIN?",
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
    "/mt5_status": "O MT5 está ligado?",
    "/mt5_positions": "Que posições estão abertas no MT5?",
    "/mt5_sync": "Sincroniza posições MT5.",
    "/mt5_healthcheck": "Executa healthcheck.",
    "/runtime": "Qual é o estado runtime do ODIN?",
    "/runtime_status": "Qual é o estado runtime do ODIN?",
    "/runtime_snapshot": "Mostra o snapshot actual.",
    "/runtime_events": "Mostra os últimos eventos.",
    "/runtime_validate": "O snapshot está válido?",
    "/soak_status": "Qual foi o último soak test?",
    "/soak_report": "Qual foi o último soak test?",
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
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    def _run_direct_command(self, text: str) -> dict[str, object] | None:
        command_map = {
            "/mt5_status": "MT5_STATUS",
            "/mt5_positions": "MT5_LIST_POSITIONS",
            "/mt5_sync": "MT5_SYNC_POSITIONS",
            "/mt5_healthcheck": "MT5_HEALTHCHECK",
            "/runtime_status": "RUNTIME_STATUS",
            "/runtime_snapshot": "RUNTIME_SNAPSHOT",
            "/runtime_pause": "RUNTIME_PAUSE",
            "/runtime_resume": "RUNTIME_RESUME",
        }
        if text == "/runtime_validate":
            result = validate_runtime_artifacts()
            return {
                "ok": result.get("status") in {"PASS", "WARNING"},
                "answer": str(result),
                "source": "runtime_validator",
            }
        if text in {"/soak_status", "/soak_report"}:
            path = Path("data/runtime/soak_tests/latest_soak_result.json")
            if not path.exists():
                return {"ok": False, "answer": "Soak report indisponível.", "source": "soak_report"}
            return {"ok": True, "answer": path.read_text(encoding="utf-8"), "source": "soak_report"}
        command = command_map.get(text)
        if not command:
            return None
        result = self.controller.execute(command, actor="assistant:telegram", role="assistant")
        return {"ok": bool(result.get("accepted", False)), "answer": str(result), "source": "command_bus"}

    def is_allowed(self, user_id: str) -> bool:
        return user_id in self.allowed_ids if self.allowed_ids else False

    def handle(self, message: TelegramMessage) -> dict[str, object]:
        self.log_messages.write("telegram_message", {"user_id": message.user_id, "text": message.text})

        if not self.is_allowed(message.user_id):
            return {"ok": False, "answer": "Utilizador não autorizado."}

        text = message.text.strip()

        if text == "/soak":
            if not message.confirmed:
                return {"ok": False, "answer": "Confirmação necessária para iniciar mini soak test."}
            result = subprocess.run(
                [sys.executable, "-m", "tools.odin_soak_test", "--mini"],
                capture_output=True,
                text=True,
                check=False,
            )
            return {
                "ok": result.returncode == 0,
                "answer": result.stdout.strip() if result.stdout.strip() else result.stderr.strip(),
                "source": "soak_runner",
            }

        if text == "/help":
            command_list = sorted(
                list(COMMAND_TO_QUESTION.keys())
                + [
                    "/ask",
                    "/llm",
                    "/llm_status",
                    "/runtime_pause",
                    "/runtime_resume",
                    "/soak",
                    "/help",
                ]
            )
            return {"ok": True, "answer": "Comandos: " + ", ".join(command_list)}

        if text in {"/llm", "/llm_status"}:
            return {"ok": True, "source": "local_llm", "answer": str(self.assistant.llm_status())}

        if text.startswith("/ask "):
            question = text[5:].strip()
            if not question:
                return {"ok": False, "answer": "Pergunta vazia."}
            return self.assistant.ask(question, channel="telegram", confirmed=message.confirmed)

        direct = self._run_direct_command(text)
        if direct is not None:
            return direct

        question = COMMAND_TO_QUESTION.get(text)
        if not question:
            return {"ok": False, "answer": "Comando não suportado."}

        if message.confirmed:
            self.log_approvals.write(
                "telegram_command_confirmed", {"user_id": message.user_id, "text": message.text}
            )

        return self.assistant.ask(question, channel="telegram", confirmed=message.confirmed)


def build_dry_run_report(bot: TelegramBot) -> dict[str, object]:
    extra = ["/ask", "/llm", "/llm_status", "/runtime_pause", "/runtime_resume", "/soak"]
    return {
        "dry_run": True,
        "token_present": bool(bot.token),
        "allowed_user_ids_count": len(bot.allowed_ids),
        "commands_count": len(COMMAND_TO_QUESTION) + len(extra),
        "commands": sorted(list(COMMAND_TO_QUESTION.keys()) + extra),
        "network_calls": "not_performed",
        "safe_mode": True,
        "llm_status": bot.assistant.llm_status(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODIN Telegram bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and command mapping without contacting Telegram",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    controller = SystemController(log_root="logs")
    bot = TelegramBot(controller)
    if args.dry_run:
        print(build_dry_run_report(bot))
        return 0

    if not bot.token:
        print("Telegram token ausente. Use --dry-run para validação segura sem ligação externa.")
        return 0

    print("Telegram bot structure ready. Configure polling/webhook externally.")
    print(bot.handle(TelegramMessage(user_id="0", text="/help")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
