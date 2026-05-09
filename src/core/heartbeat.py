from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from shared.contracts import CoreEventEnvelope, ModuleHeartbeat
from shared.enums import EventType, HeartbeatStatus, Severity
from shared.utils import utc_now


class HeartbeatSupervisor:
    def __init__(
        self,
        required_modules: list[str],
        timeout_ms: int,
        grace_count: int = 1,
        startup_timeout_ms: int = 15_000,
    ) -> None:
        self._required_modules = tuple(required_modules)
        self._timeout_ms = timeout_ms
        self._grace_count = max(1, grace_count)
        self._startup_timeout_ms = max(1, startup_timeout_ms)
        self._started_at_utc = utc_now()
        self._heartbeats: dict[str, ModuleHeartbeat] = {}
        self._missing_warned: set[str] = set()
        self._missing_unavailable: set[str] = set()

    def record_heartbeat(
        self,
        module_name: str,
        *,
        emitted_at_utc: datetime | None = None,
        observed_at_utc: datetime | None = None,
        details: dict[str, str] | None = None,
    ) -> ModuleHeartbeat:
        emitted = emitted_at_utc or utc_now()
        observed = observed_at_utc or utc_now()
        heartbeat = ModuleHeartbeat(
            module_name=module_name,
            emitted_at_utc=emitted,
            observed_at_utc=observed,
            status_code=HeartbeatStatus.OK,
            consecutive_failures=0,
            timeout_threshold_ms=self._timeout_ms,
            details=details or {},
        )
        self._heartbeats[module_name] = heartbeat
        self._missing_warned.discard(module_name)
        self._missing_unavailable.discard(module_name)
        return heartbeat

    def emit_startup_heartbeat(self, module_name: str) -> CoreEventEnvelope:
        heartbeat = self.record_heartbeat(
            module_name,
            details={
                "liveness_phase": "startup_bootstrap",
                "module_status": "initialized",
            },
        )
        return CoreEventEnvelope(
            event_type=EventType.HB_OK.value,
            source_module=module_name,
            severity=Severity.INFO,
            payload={
                "module_name": module_name,
                "emitted_at_utc": heartbeat.emitted_at_utc.isoformat(),
                "reason_code": "startup_bootstrap_heartbeat",
            },
        )

    def evaluate(self, *, now: datetime | None = None) -> list[CoreEventEnvelope]:
        now_value = now or utc_now()
        events: list[CoreEventEnvelope] = []
        delayed_threshold = timedelta(milliseconds=self._timeout_ms)
        timeout_threshold = timedelta(milliseconds=self._timeout_ms * self._grace_count)
        startup_threshold = timedelta(milliseconds=self._startup_timeout_ms)
        startup_elapsed = now_value - self._started_at_utc

        for module_name in self._required_modules:
            heartbeat = self._heartbeats.get(module_name)
            if heartbeat is None:
                if startup_elapsed > startup_threshold:
                    if module_name in self._missing_unavailable:
                        continue
                    self._missing_unavailable.add(module_name)
                    events.append(
                        CoreEventEnvelope(
                            event_type=EventType.MODULE_UNAVAILABLE.value,
                            source_module="HeartbeatSupervisor",
                            severity=Severity.CRITICAL,
                            payload={
                                "module_name": module_name,
                                "reason_code": "module_not_started_timeout",
                                "elapsed_ms": int(startup_elapsed.total_seconds() * 1000),
                                "startup_timeout_ms": self._startup_timeout_ms,
                            },
                        )
                    )
                elif module_name not in self._missing_warned:
                    self._missing_warned.add(module_name)
                    events.append(
                        CoreEventEnvelope(
                            event_type=EventType.HB_DELAYED.value,
                            source_module="HeartbeatSupervisor",
                            severity=Severity.WARN,
                            payload={
                                "module_name": module_name,
                                "reason_code": "module_not_started",
                                "elapsed_ms": int(startup_elapsed.total_seconds() * 1000),
                                "startup_timeout_ms": self._startup_timeout_ms,
                            },
                        )
                    )
                continue

            elapsed = now_value - heartbeat.observed_at_utc
            if elapsed > timeout_threshold and heartbeat.status_code != HeartbeatStatus.TIMEOUT:
                updated = replace(
                    heartbeat,
                    status_code=HeartbeatStatus.TIMEOUT,
                    consecutive_failures=heartbeat.consecutive_failures + 1,
                    observed_at_utc=now_value,
                )
                self._heartbeats[module_name] = updated
                events.append(
                    CoreEventEnvelope(
                        event_type=EventType.HB_TIMEOUT.value,
                        source_module="HeartbeatSupervisor",
                        severity=Severity.CRITICAL,
                        payload={
                            "module_name": module_name,
                            "elapsed_ms": int(elapsed.total_seconds() * 1000),
                            "timeout_threshold_ms": self._timeout_ms * self._grace_count,
                        },
                    )
                )
            elif elapsed > delayed_threshold and heartbeat.status_code == HeartbeatStatus.OK:
                updated = replace(
                    heartbeat,
                    status_code=HeartbeatStatus.DELAYED,
                    observed_at_utc=now_value,
                )
                self._heartbeats[module_name] = updated
                events.append(
                    CoreEventEnvelope(
                        event_type=EventType.HB_DELAYED.value,
                        source_module="HeartbeatSupervisor",
                        severity=Severity.WARN,
                        payload={
                            "module_name": module_name,
                            "elapsed_ms": int(elapsed.total_seconds() * 1000),
                            "timeout_threshold_ms": self._timeout_ms,
                        },
                    )
                )
        return events

    def liveness_summary(self) -> dict[str, str]:
        now_value = utc_now()
        startup_threshold = timedelta(milliseconds=self._startup_timeout_ms)
        startup_elapsed = now_value - self._started_at_utc
        summary: dict[str, str] = {}
        for module_name in self._required_modules:
            heartbeat = self._heartbeats.get(module_name)
            if heartbeat is None:
                if module_name in self._missing_unavailable:
                    summary[module_name] = "UNAVAILABLE"
                else:
                    summary[module_name] = (
                        "UNAVAILABLE" if startup_elapsed > startup_threshold else "NOT_STARTED"
                    )
                continue
            summary[module_name] = heartbeat.status_code.value
        return summary

    def required_modules(self) -> tuple[str, ...]:
        return self._required_modules
