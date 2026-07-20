"""Hermes supervisor agent catalog."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HermesAgentProfile:
    name: str
    purpose: str
    preferred_route: str
    model_tier: str
    allowed_actions: tuple[str, ...]
    time_limit_seconds: int
    iteration_limit: int
    token_budget: int
    permanent: bool = True
    safe_actions_only: bool = True
    requires_human_approval_for_code: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "preferred_route": self.preferred_route,
            "model_tier": self.model_tier,
            "allowed_actions": list(self.allowed_actions),
            "time_limit_seconds": self.time_limit_seconds,
            "iteration_limit": self.iteration_limit,
            "token_budget": self.token_budget,
            "permanent": self.permanent,
            "safe_actions_only": self.safe_actions_only,
            "requires_human_approval_for_code": self.requires_human_approval_for_code,
        }


def default_agent_profiles() -> list[HermesAgentProfile]:
    return [
        HermesAgentProfile(
            name="hermes_supervisor",
            purpose="Receber objetivos, dividir tarefas, validar resultados, gerir budgets e escaladas.",
            preferred_route="local_main",
            model_tier="local_main",
            allowed_actions=("plan", "assign", "checkpoint", "escalate", "validate"),
            time_limit_seconds=300,
            iteration_limit=12,
            token_budget=4000,
        ),
        HermesAgentProfile(
            name="odin_operator",
            purpose="Executar operacoes seguras sobre o Odin: iniciar, parar, verificar e recuperar servicos autorizados.",
            preferred_route="local_main",
            model_tier="local_main",
            allowed_actions=("run_smoke", "validate", "safe_start", "safe_stop", "service_check"),
            time_limit_seconds=180,
            iteration_limit=8,
            token_budget=2500,
        ),
        HermesAgentProfile(
            name="odin_observer",
            purpose="Observar continuamente o Odin, recolher sinais de degradacao e emitir eventos.",
            preferred_route="local_fast",
            model_tier="local_fast",
            allowed_actions=("observe", "collect_metrics", "check_endpoints", "report"),
            time_limit_seconds=120,
            iteration_limit=6,
            token_budget=1800,
        ),
        HermesAgentProfile(
            name="log_analyst",
            purpose="Analisar logs, correlacionar erros e resumir incidentes.",
            preferred_route="local_main",
            model_tier="local_main",
            allowed_actions=("read_logs", "classify", "summarize", "recommend"),
            time_limit_seconds=180,
            iteration_limit=8,
            token_budget=2400,
        ),
        HermesAgentProfile(
            name="test_runner",
            purpose="Executar testes, comparar resultados e identificar regressões.",
            preferred_route="local_main",
            model_tier="local_main",
            allowed_actions=("run_tests", "compare_results", "report"),
            time_limit_seconds=300,
            iteration_limit=6,
            token_budget=2200,
        ),
        HermesAgentProfile(
            name="memory_keeper",
            purpose="Manter memoria operacional, de projeto, de solucoes e checkpoints.",
            preferred_route="local_fast",
            model_tier="local_fast",
            allowed_actions=("store_memory", "deduplicate", "summarize", "restore_context"),
            time_limit_seconds=120,
            iteration_limit=8,
            token_budget=1600,
        ),
        HermesAgentProfile(
            name="skill_builder",
            purpose="Identificar procedimentos repetitivos e convertê-los em skills reutilizaveis.",
            preferred_route="local_main",
            model_tier="local_main",
            allowed_actions=("catalog", "document", "version", "validate_structure"),
            time_limit_seconds=240,
            iteration_limit=8,
            token_budget=2600,
        ),
        HermesAgentProfile(
            name="resource_guardian",
            purpose="Monitorizar CPU, RAM, disco e disponibilidade local de GPU/modelos.",
            preferred_route="local_fast",
            model_tier="local_fast",
            allowed_actions=("monitor_resources", "degrade_mode", "alert"),
            time_limit_seconds=90,
            iteration_limit=4,
            token_budget=1200,
        ),
        HermesAgentProfile(
            name="risk_guardian",
            purpose="Aplicar regras deterministicas de seguranca, bloqueando trading real e acoes destrutivas.",
            preferred_route="local_fast",
            model_tier="local_fast",
            allowed_actions=("validate_action", "block", "audit"),
            time_limit_seconds=90,
            iteration_limit=4,
            token_budget=1200,
        ),
        HermesAgentProfile(
            name="codex_coordinator",
            purpose="Preparar tarefas pequenas para o Codex e validar o resultado sem merge automatico.",
            preferred_route="codex",
            model_tier="codex",
            allowed_actions=("prepare_task", "collect_context", "validate_diff", "run_post_checks"),
            time_limit_seconds=240,
            iteration_limit=6,
            token_budget=1800,
        ),
        HermesAgentProfile(
            name="telegram_reporter",
            purpose="Emitir estado e alertas por Telegram quando configurado.",
            preferred_route="local_fast",
            model_tier="local_fast",
            allowed_actions=("format_report", "send_alert", "request_confirmation"),
            time_limit_seconds=60,
            iteration_limit=4,
            token_budget=800,
        ),
    ]


def build_temporary_agent(
    *,
    name: str,
    purpose: str,
    allowed_actions: tuple[str, ...],
    preferred_route: str,
    model_tier: str,
    time_limit_seconds: int,
    iteration_limit: int,
    token_budget: int,
) -> HermesAgentProfile:
    return HermesAgentProfile(
        name=name,
        purpose=purpose,
        preferred_route=preferred_route,
        model_tier=model_tier,
        allowed_actions=allowed_actions,
        time_limit_seconds=time_limit_seconds,
        iteration_limit=iteration_limit,
        token_budget=token_budget,
        permanent=False,
    )
