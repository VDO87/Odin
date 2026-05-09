from __future__ import annotations

from shared.contracts import ActiveBlockVector, PersistentKillState, StartupValidationResult
from shared.enums import GlobalState
from shared.utils import utc_now
from persistence.state_store import PersistentStateStore


class StartupOrchestrator:
    def __init__(self, store: PersistentStateStore, required_modules: list[str]) -> None:
        self._store = store
        self._required_modules = tuple(required_modules)

    def validate(
        self,
        *,
        configuration_ok: bool = True,
        modules_alive: dict[str, bool] | None = None,
    ) -> StartupValidationResult:
        alive_map = modules_alive or {}
        persistence_ok = self._store.validate_integrity()
        kill_state = self._store.read_kill_state() or PersistentKillState.inactive()
        block_vector = self._store.read_latest_block_vector() or ActiveBlockVector.empty()
        shutdown_marker = self._store.read_shutdown_marker()
        required_modules_ok = all(alive_map.get(module, True) for module in self._required_modules)
        notes: list[str] = []

        if not configuration_ok:
            notes.append("configuration_invalid")
        if not persistence_ok:
            notes.append("persistence_invalid")
        if kill_state.is_active:
            notes.append("kill_active")
        if not required_modules_ok:
            notes.append("required_module_unavailable")
        if shutdown_marker is not None and not shutdown_marker.clean_shutdown:
            notes.append("unclean_shutdown_detected")

        if not configuration_ok or not persistence_ok or kill_state.is_active or not required_modules_ok:
            recommended_state = GlobalState.BLOCKED_FAULT
        elif shutdown_marker is not None and not shutdown_marker.clean_shutdown:
            recommended_state = GlobalState.RECOVERY
        else:
            recommended_state = GlobalState.STARTUP

        result = StartupValidationResult(
            configuration_ok=configuration_ok,
            persistence_ok=persistence_ok,
            required_modules_ok=required_modules_ok,
            kill_active=kill_state.is_active,
            block_vector_loaded=block_vector.active_block_count >= 0,
            recommended_entry_state=recommended_state,
            operator_action_required=kill_state.is_active or not configuration_ok or not persistence_ok,
            validation_notes=tuple(notes),
        )
        self._store.mark_startup_in_progress(result.startup_id, utc_now())
        return result
