from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shared.enums import AssetClass, ExecutionVenue, OrderWorkflow, PortfolioBucket
from shared.utils import ensure_utc, make_id, utc_now


OPERATOR_COMMANDS_V1: tuple[str, ...] = (
    "status",
    "stop",
    "pause",
    "resume",
    "export-logs",
    "get-config",
    "validate-config",
)


@dataclass(frozen=True, slots=True)
class OperatorCommandRequest:
    command: str
    requested_by: str
    role: str
    authorization_context: dict[str, Any] = field(default_factory=dict)
    confirmation: bool = False
    request_id: str = field(default_factory=lambda: make_id("op-cmd"))
    requested_at_utc: datetime = field(default_factory=utc_now)
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_at_utc", ensure_utc(self.requested_at_utc))
        if not self.command:
            raise ValueError("command is required")
        if not self.requested_by:
            raise ValueError("requested_by is required")
        if not self.role:
            raise ValueError("role is required")


@dataclass(frozen=True, slots=True)
class OperatorCommandResult:
    request_id: str
    command: str
    accepted: bool
    response: dict[str, Any] = field(default_factory=dict)
    rejection_reason: str | None = None
    confirmation_required: bool = False
    completed_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "completed_at_utc", ensure_utc(self.completed_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "command": self.command,
            "accepted": self.accepted,
            "response": self.response,
            "rejection_reason": self.rejection_reason,
            "confirmation_required": self.confirmation_required,
            "completed_at_utc": self.completed_at_utc.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ConfigStagingPatch:
    patch: dict[str, Any]
    staged_by: str
    stage_id: str = field(default_factory=lambda: make_id("cfg-stage"))
    staged_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "staged_at_utc", ensure_utc(self.staged_at_utc))
        if not self.staged_by:
            raise ValueError("staged_by is required")


@dataclass(frozen=True, slots=True)
class ConfigValidationReport:
    is_valid: bool
    profile: str
    dashboard_surface: str
    errors: tuple[str, ...] = tuple()
    warnings: tuple[str, ...] = tuple()
    validated_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "validated_at_utc", ensure_utc(self.validated_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "profile": self.profile,
            "dashboard_surface": self.dashboard_surface,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "validated_at_utc": self.validated_at_utc.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class InternalChatAdvisoryRequest:
    prompt: str
    requested_by: str
    allow_control_suggestions: bool = True
    allow_critical_actions: bool = False
    requires_confirmation_for_actions: bool = True
    context_ref: str | None = None
    request_id: str = field(default_factory=lambda: make_id("chat-req"))
    requested_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_at_utc", ensure_utc(self.requested_at_utc))
        if not self.prompt:
            raise ValueError("prompt is required")
        if not self.requested_by:
            raise ValueError("requested_by is required")


@dataclass(frozen=True, slots=True)
class InternalChatAdvisoryResponse:
    request_id: str
    advisory_text: str
    suggested_commands: tuple[str, ...] = tuple()
    blocked_commands: tuple[str, ...] = tuple()
    response_id: str = field(default_factory=lambda: make_id("chat-rsp"))
    responded_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "responded_at_utc", ensure_utc(self.responded_at_utc))


@dataclass(frozen=True, slots=True)
class TelegramBridgeEnvelope:
    chat_id: str
    sender_id: str
    sender_role: str
    message_text: str
    allow_non_critical_commands: bool = True
    forbid_order_execution: bool = True
    require_confirmation_for_critical: bool = True
    enforce_via_command_gateway: bool = True
    envelope_id: str = field(default_factory=lambda: make_id("tg-envelope"))
    received_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "received_at_utc", ensure_utc(self.received_at_utc))
        if not self.chat_id:
            raise ValueError("chat_id is required")
        if not self.sender_id:
            raise ValueError("sender_id is required")
        if not self.message_text:
            raise ValueError("message_text is required")
        if not self.forbid_order_execution:
            raise ValueError("Telegram bridge cannot execute orders directly")
        if not self.require_confirmation_for_critical:
            raise ValueError("Telegram bridge requires critical confirmation")
        if not self.enforce_via_command_gateway:
            raise ValueError("Telegram bridge must be routed via CommandGateway")


@dataclass(frozen=True, slots=True)
class OpenAIAdvisoryRequest:
    advisory_context_ref: str
    profile: str
    question: str
    forbid_state_mutation: bool = True
    forbid_order_execution: bool = True
    request_id: str = field(default_factory=lambda: make_id("openai-adv-req"))
    requested_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_at_utc", ensure_utc(self.requested_at_utc))
        if not self.advisory_context_ref:
            raise ValueError("advisory_context_ref is required")
        if not self.question:
            raise ValueError("question is required")


@dataclass(frozen=True, slots=True)
class OpenAIAdvisoryResponse:
    request_id: str
    advisory_text: str
    model_hint: str | None = None
    advisory_snapshot_ref: str | None = None
    response_id: str = field(default_factory=lambda: make_id("openai-adv-rsp"))
    responded_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "responded_at_utc", ensure_utc(self.responded_at_utc))


@dataclass(frozen=True, slots=True)
class ExecAdapterBridgeRequest:
    adapter_name: str
    adapter_type: str
    direction: str
    payload: dict[str, Any]
    execution_venue: str = ExecutionVenue.MT5.value
    asset_class: str = AssetClass.FOREX.value
    portfolio_bucket: str = PortfolioBucket.SHORT_TERM_TRADING.value
    workflow: str = OrderWorkflow.AUTO_DEMO.value
    request_id: str = field(default_factory=lambda: make_id("exec-bridge-req"))
    requested_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_at_utc", ensure_utc(self.requested_at_utc))
        if not self.adapter_name:
            raise ValueError("adapter_name is required")
        venue = ExecutionVenue(self.execution_venue)
        adapter = ExecutionVenue(self.adapter_type)
        if venue != adapter:
            raise ValueError("execution_venue must match adapter_type")
        asset = AssetClass(self.asset_class)
        bucket = PortfolioBucket(self.portfolio_bucket)
        workflow = OrderWorkflow(self.workflow)

        if venue == ExecutionVenue.MT5:
            if asset != AssetClass.FOREX:
                raise ValueError("MT5 initial scope is FOREX")
            if workflow not in {OrderWorkflow.AUTO_DEMO, OrderWorkflow.MANUAL_CONFIRMATION}:
                raise ValueError("MT5 initial workflow must be AUTO_DEMO or MANUAL_CONFIRMATION")
            if workflow == OrderWorkflow.AUTO_DEMO and bucket != PortfolioBucket.SHORT_TERM_TRADING:
                raise ValueError("MT5 AUTO_DEMO must target SHORT_TERM_TRADING")

        if venue == ExecutionVenue.XTB:
            if workflow == OrderWorkflow.AUTO_REAL:
                raise ValueError("XTB real execution is prepared but not active")
            if workflow == OrderWorkflow.AUTO_DEMO:
                raise ValueError("XTB initial workflow is assisted/manual, not AUTO_DEMO")
            if workflow == OrderWorkflow.TELEGRAM_ASSISTED and bucket == PortfolioBucket.SHORT_TERM_TRADING:
                raise ValueError("XTB TELEGRAM_ASSISTED is reserved for medium/long-term buckets")
            if workflow == OrderWorkflow.TELEGRAM_ASSISTED and asset not in {AssetClass.ETF, AssetClass.STOCK}:
                raise ValueError("XTB TELEGRAM_ASSISTED initial scope is ETF/STOCK")


@dataclass(frozen=True, slots=True)
class ExecAdapterBridgeResponse:
    request_id: str
    accepted: bool
    adapter_name: str
    adapter_type: str
    execution_venue: str = ExecutionVenue.MT5.value
    asset_class: str = AssetClass.FOREX.value
    portfolio_bucket: str = PortfolioBucket.SHORT_TERM_TRADING.value
    workflow: str = OrderWorkflow.AUTO_DEMO.value
    response_payload: dict[str, Any] = field(default_factory=dict)
    rejection_reason: str | None = None
    response_id: str = field(default_factory=lambda: make_id("exec-bridge-rsp"))
    responded_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "responded_at_utc", ensure_utc(self.responded_at_utc))
        _ = ExecutionVenue(self.adapter_type)
        _ = ExecutionVenue(self.execution_venue)
        _ = AssetClass(self.asset_class)
        _ = PortfolioBucket(self.portfolio_bucket)
        _ = OrderWorkflow(self.workflow)
