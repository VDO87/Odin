"""Hermes skill library metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HermesSkillDefinition:
    name: str
    description: str
    purpose: str
    parameters: tuple[str, ...]
    permissions: tuple[str, ...]
    preconditions: tuple[str, ...]
    validations: tuple[str, ...]
    expected_result: str
    possible_errors: tuple[str, ...]
    recovery_strategy: str
    tests: tuple[str, ...]
    version: str

    def skill_path(self, project_root: Path) -> Path:
        return project_root / ".agents" / "skills" / self.name / "SKILL.md"

    def to_dict(self, project_root: Path) -> dict[str, object]:
        path = self.skill_path(project_root)
        return {
            "name": self.name,
            "description": self.description,
            "purpose": self.purpose,
            "parameters": list(self.parameters),
            "permissions": list(self.permissions),
            "preconditions": list(self.preconditions),
            "validations": list(self.validations),
            "expected_result": self.expected_result,
            "possible_errors": list(self.possible_errors),
            "recovery_strategy": self.recovery_strategy,
            "tests": list(self.tests),
            "version": self.version,
            "path": str(path),
            "exists": path.exists(),
        }


def default_skill_definitions() -> list[HermesSkillDefinition]:
    return [
        _skill("verificar_estado_odin", "Inspecionar o estado atual do Odin.", ("ler_estado", "executar_smoke"), ("read_files", "run_safe_checks")),
        _skill("iniciar_odin", "Iniciar o Odin em modo seguro.", ("modo", "componentes"), ("safe_start", "read_logs")),
        _skill("parar_odin", "Parar o Odin de forma segura.", ("componentes",), ("safe_stop", "read_logs")),
        _skill("reiniciar_servico_odin", "Reiniciar um servico autorizado do Odin.", ("servico",), ("service_restart_safe", "health_check")),
        _skill("verificar_ollama", "Verificar disponibilidade do Ollama local.", ("timeout_segundos",), ("probe_local_provider",)),
        _skill("verificar_modelo_local", "Verificar um modelo local especifico.", ("modelo",), ("probe_local_provider", "model_lookup")),
        _skill("analisar_logs_recentes", "Ler e resumir logs recentes do Odin.", ("limite_linhas",), ("read_logs",)),
        _skill("identificar_erro_recorrente", "Agrupar erros repetidos e propor classificacao.", ("janela",), ("read_logs", "summarize")),
        _skill("executar_testes", "Executar testes seguros do projeto.", ("alvo", "watchdog"), ("run_tests",)),
        _skill("gerar_relatorio_testes", "Resumir resultados de testes e regressões.", ("origem",), ("read_test_results", "summarize")),
        _skill("criar_checkpoint", "Guardar checkpoint persistente do objetivo atual.", ("goal_id", "resumo"), ("write_memory", "write_checkpoint")),
        _skill("recuperar_checkpoint", "Recuperar o ultimo checkpoint persistente.", ("goal_id",), ("read_memory", "read_checkpoint")),
        _skill("monitorizar_recursos", "Recolher recursos locais e degradar se necessario.", ("amostragem",), ("read_resources",)),
        _skill("compactar_contexto", "Compactar contexto operacional para reduzir tokens.", ("scope",), ("summarize", "write_memory")),
        _skill("resumir_sessao", "Produzir resumo incremental da sessao.", ("scope",), ("summarize", "write_memory")),
        _skill("recuperar_memoria", "Recuperar memoria relevante para uma tarefa.", ("scope", "query"), ("read_memory",)),
        _skill("criar_tarefa_codex", "Preparar tarefa pequena e auditavel para o Codex.", ("objetivo", "ficheiros"), ("prepare_codex_task",)),
        _skill("validar_resultado_codex", "Validar diff, testes e restricoes apos trabalho do Codex.", ("diff",), ("run_tests", "review_diff")),
        _skill("verificar_git_status", "Inspecionar git status e commit atual.", tuple(), ("read_git",)),
        _skill("criar_branch_trabalho", "Criar branch de trabalho sem merge automatico.", ("nome_branch",), ("git_branch_safe",)),
        _skill("gerar_relatorio_telegram", "Formatar estado e alertas para Telegram.", ("canal",), ("format_report",)),
        _skill("executar_safe_stop", "Colocar supervisor e Odin em modo SAFE_STOP.", ("motivo",), ("safe_stop", "write_memory")),
    ]


def skill_library_status(project_root: Path) -> list[dict[str, object]]:
    return [definition.to_dict(project_root) for definition in default_skill_definitions()]


def _skill(
    name: str,
    purpose: str,
    parameters: tuple[str, ...],
    permissions: tuple[str, ...],
) -> HermesSkillDefinition:
    return HermesSkillDefinition(
        name=name,
        description=f"Skill operacional Hermes para {name.replace('_', ' ')}.",
        purpose=purpose,
        parameters=parameters,
        permissions=permissions,
        preconditions=("REAL_TRADING=false", "SAFE_TO_TRADE=false"),
        validations=("resultado_estruturado", "flags_criticos_false"),
        expected_result="Resultado seguro e auditavel, sem desbloquear trading real.",
        possible_errors=("dependencia_ausente", "timeout", "estado_invalido"),
        recovery_strategy="Registrar incidente, manter fail-closed e escalar apenas com contexto minimo.",
        tests=("estrutura_skill", "validacao_registry"),
        version="1.0.0",
    )
