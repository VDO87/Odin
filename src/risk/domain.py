from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from market.domain import ContextState, MarketAssessment, MarketReadiness, MarketState, SpreadState
from shared.contracts import CoreEventEnvelope
from shared.enums import OperationalMode
from shared.enums import EventType, Severity
from shared.utils import ensure_utc, isoformat_utc, utc_now


class RiskDecision(StrEnum):
    ALLOW = "ALLOW"
    RESTRICT = "RESTRICT"
    BLOCK = "BLOCK"
    KILL = "KILL"


class RiskState(StrEnum):
    NORMAL = "RS-10"
    RESTRICTED = "RS-20"
    BLOCKED = "RS-30"
    KILL_ACTIVE = "RS-40"
    DEGRADED = "RS-50"


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    risk_state: RiskState
    risk_decision: RiskDecision
    kill_active: bool
    dominant_risk_reason: str
    risk_snapshot_ref: str | None = None
    cooldown_active: bool = False
    reason_text: str | None = None
    evaluated_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evaluated_at_utc", ensure_utc(self.evaluated_at_utc))
        if not self.dominant_risk_reason:
            raise ValueError("dominant_risk_reason is required")

    @property
    def event_type(self) -> str:
        if self.kill_active or self.risk_decision == RiskDecision.KILL:
            return EventType.KILL_ACTIVE.value
        if self.risk_decision == RiskDecision.BLOCK:
            return EventType.RISK_BLOCK.value
        if self.risk_decision == RiskDecision.RESTRICT:
            return EventType.RISK_RESTRICT.value
        return EventType.RISK_ALLOW.value

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "risk_state": self.risk_state.value,
            "risk_decision": self.risk_decision.value,
            "allowance_class": self.risk_decision.value,
            "reason_code": self.dominant_risk_reason,
            "kill_active": self.kill_active,
            "dominant_risk_reason": self.dominant_risk_reason,
            "cooldown_active": self.cooldown_active,
            "evaluated_at_utc": isoformat_utc(self.evaluated_at_utc),
        }
        if self.risk_snapshot_ref:
            payload["risk_snapshot_ref"] = self.risk_snapshot_ref
        if self.reason_text:
            payload["reason_text"] = self.reason_text
        return payload

    def to_core_event(self, source_module: str = "RISK") -> CoreEventEnvelope:
        severity = {
            EventType.RISK_ALLOW.value: Severity.INFO,
            EventType.RISK_RESTRICT.value: Severity.WARN,
            EventType.RISK_BLOCK.value: Severity.ERROR,
            EventType.KILL_ACTIVE.value: Severity.CRITICAL,
        }[self.event_type]
        return CoreEventEnvelope(
            event_type=self.event_type,
            source_module=source_module,
            severity=severity,
            payload=self.to_payload(),
        )


@dataclass(frozen=True, slots=True)
class RiskInput:
    market: MarketAssessment
    current_daily_pnl: float = 0.0
    max_daily_loss: float = 500.0
    kill_loss_multiplier: float = 1.5
    open_positions_count: int = 0
    max_open_positions: int = 1
    consecutive_losses: int = 0
    max_consecutive_losses: int = 3
    cooldown_active: bool = False
    kill_switch_active: bool = False
    policy_loaded: bool = True
    current_mode: OperationalMode = OperationalMode.DEMO
    expected_operation_impact: float | None = None
    max_risk_per_operation: float = 100.0
    risk_snapshot_ref: str | None = None

    def __post_init__(self) -> None:
        if self.max_daily_loss <= 0:
            raise ValueError("max_daily_loss must be > 0")
        if self.kill_loss_multiplier < 1.0:
            raise ValueError("kill_loss_multiplier must be >= 1.0")
        if self.max_open_positions < 0:
            raise ValueError("max_open_positions must be >= 0")
        if self.max_consecutive_losses < 0:
            raise ValueError("max_consecutive_losses must be >= 0")
        if self.max_risk_per_operation <= 0:
            raise ValueError("max_risk_per_operation must be > 0")


class RiskEvaluator:
    def evaluate(self, risk_input: RiskInput) -> RiskAssessment:
        if risk_input.kill_switch_active:
            return RiskAssessment(
                risk_state=RiskState.KILL_ACTIVE,
                risk_decision=RiskDecision.KILL,
                kill_active=True,
                dominant_risk_reason="kill_switch_active",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        if not risk_input.policy_loaded:
            return RiskAssessment(
                risk_state=RiskState.BLOCKED,
                risk_decision=RiskDecision.BLOCK,
                kill_active=False,
                dominant_risk_reason="risk_policy_unavailable",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        kill_limit = -abs(risk_input.max_daily_loss) * risk_input.kill_loss_multiplier
        if risk_input.current_daily_pnl <= kill_limit:
            return RiskAssessment(
                risk_state=RiskState.KILL_ACTIVE,
                risk_decision=RiskDecision.KILL,
                kill_active=True,
                dominant_risk_reason="daily_loss_kill_threshold",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        if risk_input.current_daily_pnl <= -abs(risk_input.max_daily_loss):
            return RiskAssessment(
                risk_state=RiskState.BLOCKED,
                risk_decision=RiskDecision.BLOCK,
                kill_active=False,
                dominant_risk_reason="daily_loss_limit_reached",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        if (
            risk_input.max_consecutive_losses > 0
            and risk_input.consecutive_losses >= risk_input.max_consecutive_losses
        ):
            return RiskAssessment(
                risk_state=RiskState.BLOCKED,
                risk_decision=RiskDecision.BLOCK,
                kill_active=False,
                dominant_risk_reason="consecutive_loss_limit_reached",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        if (
            risk_input.max_open_positions >= 0
            and risk_input.open_positions_count >= risk_input.max_open_positions
        ):
            return RiskAssessment(
                risk_state=RiskState.BLOCKED,
                risk_decision=RiskDecision.BLOCK,
                kill_active=False,
                dominant_risk_reason="open_position_limit_reached",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        market = risk_input.market
        if market.market_state in {
            MarketState.INVALID,
            MarketState.CLOSED,
            MarketState.UNAVAILABLE,
        } or market.readiness_state in {MarketReadiness.NOT_READY, MarketReadiness.UNAVAILABLE}:
            return RiskAssessment(
                risk_state=RiskState.BLOCKED,
                risk_decision=RiskDecision.BLOCK,
                kill_active=False,
                dominant_risk_reason="market_not_ready",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        if market.context_state == ContextState.HOSTILE or market.spread_state == SpreadState.CRITICAL:
            return RiskAssessment(
                risk_state=RiskState.BLOCKED,
                risk_decision=RiskDecision.BLOCK,
                kill_active=False,
                dominant_risk_reason="market_context_hostile",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        if risk_input.cooldown_active:
            return RiskAssessment(
                risk_state=RiskState.RESTRICTED,
                risk_decision=RiskDecision.RESTRICT,
                kill_active=False,
                dominant_risk_reason="risk_cooldown_active",
                cooldown_active=True,
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        if risk_input.current_mode == OperationalMode.REAL:
            if risk_input.expected_operation_impact is None:
                return RiskAssessment(
                    risk_state=RiskState.RESTRICTED,
                    risk_decision=RiskDecision.RESTRICT,
                    kill_active=False,
                    dominant_risk_reason="real_mode_requires_operation_impact",
                    risk_snapshot_ref=risk_input.risk_snapshot_ref,
                )
            if abs(risk_input.expected_operation_impact) >= abs(risk_input.max_risk_per_operation):
                return RiskAssessment(
                    risk_state=RiskState.BLOCKED,
                    risk_decision=RiskDecision.BLOCK,
                    kill_active=False,
                    dominant_risk_reason="real_mode_operation_limit_exceeded",
                    risk_snapshot_ref=risk_input.risk_snapshot_ref,
                )
            if abs(risk_input.expected_operation_impact) >= abs(risk_input.max_risk_per_operation) * 0.5:
                return RiskAssessment(
                    risk_state=RiskState.RESTRICTED,
                    risk_decision=RiskDecision.RESTRICT,
                    kill_active=False,
                    dominant_risk_reason="real_mode_operation_limit_restricted",
                    risk_snapshot_ref=risk_input.risk_snapshot_ref,
                )

        if (
            market.market_state == MarketState.DEGRADED
            or market.context_state == ContextState.SENSITIVE
            or market.readiness_state == MarketReadiness.READY_RESTRICTED
            or market.spread_state == SpreadState.WIDE
            or market.news_guard_active
        ):
            return RiskAssessment(
                risk_state=RiskState.DEGRADED,
                risk_decision=RiskDecision.RESTRICT,
                kill_active=False,
                dominant_risk_reason="market_requires_restriction",
                risk_snapshot_ref=risk_input.risk_snapshot_ref,
            )

        return RiskAssessment(
            risk_state=RiskState.NORMAL,
            risk_decision=RiskDecision.ALLOW,
            kill_active=False,
            dominant_risk_reason="risk_within_limits",
            risk_snapshot_ref=risk_input.risk_snapshot_ref,
        )
