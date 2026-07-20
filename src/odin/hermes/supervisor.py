"""Hermes local-first supervisor runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from odin.contracts.events import (
    HERMES_AGENT_CATALOG_SYNCED,
    HERMES_GOAL_ENGINE_UPDATED,
    HERMES_MEMORY_UPDATED,
    HERMES_SKILL_CATALOG_SYNCED,
    HERMES_SUPERVISOR_CYCLE_COMPLETED,
    HERMES_SUPERVISOR_CYCLE_DEGRADED,
    HERMES_SUPERVISOR_CYCLE_STARTED,
    OdinEvent,
)
from odin.hermes.agents import default_agent_profiles
from odin.hermes.goals import SUPPORTED_GOAL_STATES, bootstrap_supervisor_goal
from odin.hermes.skills_registry import skill_library_status
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


def run_hermes_supervisor(
    *,
    cycles: int = 1,
    sleep_seconds: int = 0,
    project_root: str = ".",
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
    command_overrides: dict[str, tuple[bool, str]] | None = None,
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    project_path = Path(project_root).resolve()
    last_report: dict[str, object] = {}
    cycles = max(cycles, 1)
    for index in range(cycles):
        _audit(logger, store, run_id, HERMES_SUPERVISOR_CYCLE_STARTED, {"cycle_index": index + 1})
        last_report = _run_cycle(
            logger=logger,
            store=store,
            run_id=run_id,
            project_root=project_path,
            command_overrides=command_overrides or {},
            cycle_index=index + 1,
            cycles_total=cycles,
        )
        event_name = (
            HERMES_SUPERVISOR_CYCLE_COMPLETED
            if last_report["status"] == "OK"
            else HERMES_SUPERVISOR_CYCLE_DEGRADED
        )
        _audit(logger, store, run_id, event_name, {"cycle_index": index + 1, "status": last_report["status"]})
        if index + 1 < cycles and sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return last_report


def _run_cycle(
    *,
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    project_root: Path,
    command_overrides: dict[str, tuple[bool, str]],
    cycle_index: int,
    cycles_total: int,
) -> dict[str, object]:
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    agents = [agent.to_dict() for agent in default_agent_profiles()]
    skills = skill_library_status(project_root)
    goal = bootstrap_supervisor_goal(timestamp).to_dict()

    local_provider = _probe_local_provider(command_overrides)
    codex_available = _probe_command("codex_version", ["codex", "--version"], command_overrides)[0]
    git_available = _probe_command("git_version", ["git", "--version"], command_overrides)[0]
    telegram_configured = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
    resources = _resource_snapshot(project_root, command_overrides)

    warnings: list[str] = []
    if not local_provider["ollama_available"]:
        warnings.append("Ollama nao encontrado; supervisor fica em modo degradado sem provider local ativo.")
    if local_provider["ollama_available"] and not local_provider["models"]:
        warnings.append("Ollama encontrado sem modelos locais carregados no momento.")
    if not telegram_configured:
        warnings.append("Telegram nao configurado; telegram_reporter fica em standby.")

    status = "OK" if local_provider["ollama_available"] and skills else "DEGRADED"
    operational_state = "LOCAL_ONLY" if local_provider["ollama_available"] else "MODEL_UNAVAILABLE"

    routing = {
        "default": "local_main",
        "flow": [
            "SKILL_EXISTENTE",
            "AGENTE_LOCAL",
            "LLM_LOCAL",
            "SEGUNDO_MODELO_LOCAL",
            "MODELO_CLOUD",
            "CODEX",
        ],
        "cloud_without_reason_blocked": True,
        "codex_last_resort": True,
        "local_attempts_before_escalation": 2,
    }

    report = {
        "status": status,
        "component": "hermes_supervisor",
        "operational_state": operational_state,
        "cycles_completed": cycle_index,
        "cycles_requested": cycles_total,
        "safe_actions_only": True,
        "read_only_finance_controls": True,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
        "local_provider": local_provider,
        "routing": routing,
        "codex_available": codex_available,
        "git_available": git_available,
        "telegram_configured": telegram_configured,
        "agents_count": len(agents),
        "skills_count": len(skills),
        "agents": agents,
        "skills": skills,
        "goal_engine": {
            "persistent": True,
            "supported_states": list(SUPPORTED_GOAL_STATES),
            "active_goal": goal["goal_id"],
            "next_step": goal["next_step"],
        },
        "memory_layers": {
            "operational": True,
            "project": True,
            "solutions": True,
            "checkpoints": True,
            "sqlite": True,
            "jsonl": True,
        },
        "resource_guardian": resources,
        "authorized_autonomy": [
            "read_files",
            "read_logs",
            "run_tests",
            "generate_reports",
            "update_memory",
            "prepare_codex_task",
            "safe_stop",
        ],
        "service_control_supported": False,
        "warnings": warnings,
    }

    store.register_agents(agents)
    store.register_skills(skills)
    store.upsert_hermes_goal(goal)
    store.upsert_hermes_memory("operational", "current_cycle", report)
    store.upsert_hermes_memory(
        "project",
        "architecture",
        {
            "project_root": str(project_root),
            "routing_default": routing["default"],
            "skills_count": len(skills),
            "agents_count": len(agents),
        },
    )
    store.create_hermes_checkpoint(
        checkpoint_id=f"{goal['goal_id']}-{cycle_index}",
        goal_id=goal["goal_id"],
        summary="Hermes supervisor cycle completed in safe mode.",
        state=report,
    )
    store.record_hermes_runtime(report)

    _audit(logger, store, run_id, HERMES_AGENT_CATALOG_SYNCED, {"agents_count": len(agents)})
    _audit(logger, store, run_id, HERMES_SKILL_CATALOG_SYNCED, {"skills_count": len(skills)})
    _audit(logger, store, run_id, HERMES_GOAL_ENGINE_UPDATED, goal)
    _audit(
        logger,
        store,
        run_id,
        HERMES_MEMORY_UPDATED,
        {"scopes": ["operational", "project"], "checkpoint_id": f"{goal['goal_id']}-{cycle_index}"},
    )
    return report


def _probe_local_provider(
    command_overrides: dict[str, tuple[bool, str]],
) -> dict[str, object]:
    version_ok, version_output = _probe_ollama_command("ollama_version", ["--version"], command_overrides)
    list_ok, list_output = _probe_ollama_command("ollama_list", ["list"], command_overrides)
    models = _parse_ollama_models(list_output) if list_ok else []
    return {
        "provider": "ollama",
        "ollama_available": version_ok,
        "version": version_output.strip() if version_ok else "",
        "models": models,
        "primary_model_target": "local_main",
        "fast_model_target": "local_fast",
    }


def _resource_snapshot(
    project_root: Path,
    command_overrides: dict[str, tuple[bool, str]],
) -> dict[str, object]:
    disk = shutil.disk_usage(project_root)
    load_average = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
    memory_total_mb = 0
    memory_available_mb = 0
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        data: dict[str, int] = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            amount = value.strip().split()[0]
            if amount.isdigit():
                data[key] = int(amount)
        memory_total_mb = data.get("MemTotal", 0) // 1024
        memory_available_mb = data.get("MemAvailable", 0) // 1024

    nvidia_ok, nvidia_output = _probe_command("nvidia_smi", ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"], command_overrides)
    return {
        "cpu_load_1m": round(load_average, 2),
        "memory_total_mb": memory_total_mb,
        "memory_available_mb": memory_available_mb,
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "disk_free_gb": round(disk.free / (1024 ** 3), 2),
        "gpu_probe_available": nvidia_ok,
        "gpu_probe_output": nvidia_output.strip() if nvidia_ok else "",
    }


def _probe_ollama_command(
    key: str,
    suffix: list[str],
    command_overrides: dict[str, tuple[bool, str]],
) -> tuple[bool, str]:
    if key in command_overrides:
        return command_overrides[key]
    candidates = [
        ["ollama", *suffix],
        ["/mnt/c/Users/ODIN/AppData/Local/Programs/Ollama/ollama.exe", *suffix],
    ]
    for args in candidates:
        ok, output = _probe_command(key, args, command_overrides)
        if ok:
            return ok, output
    return False, ""


def _probe_command(
    key: str,
    args: list[str],
    command_overrides: dict[str, tuple[bool, str]],
) -> tuple[bool, str]:
    if key in command_overrides:
        return command_overrides[key]
    try:
        completed = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, PermissionError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False, ""
    return True, completed.stdout or completed.stderr


def _parse_ollama_models(output: str) -> list[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) <= 1:
        return []
    models: list[str] = []
    for line in lines[1:]:
        models.append(line.split()[0])
    return models


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.hermes_supervisor",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)
