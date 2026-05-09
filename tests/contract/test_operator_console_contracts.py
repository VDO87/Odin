import pytest

from shared.contracts import (
    ConfigValidationReport,
    ExecAdapterBridgeRequest,
    OpenAIAdvisoryRequest,
    OperatorCommandRequest,
    OperatorCommandResult,
    TelegramBridgeEnvelope,
)


def test_operator_command_result_to_dict_contains_expected_fields() -> None:
    result = OperatorCommandResult(
        request_id="op-cmd-1",
        command="status",
        accepted=True,
        response={"global_state": "ST-30"},
    )

    payload = result.to_dict()

    assert payload["request_id"] == "op-cmd-1"
    assert payload["command"] == "status"
    assert payload["accepted"] is True
    assert payload["response"]["global_state"] == "ST-30"


def test_operator_command_request_requires_identity_fields() -> None:
    with pytest.raises(ValueError):
        OperatorCommandRequest(command="status", requested_by="", role="operator")

    with pytest.raises(ValueError):
        OperatorCommandRequest(command="", requested_by="op-1", role="operator")


def test_config_validation_report_serialization() -> None:
    report = ConfigValidationReport(
        is_valid=False,
        profile="lite",
        dashboard_surface="lite",
        errors=("invalid_scope",),
    )

    payload = report.to_dict()
    assert payload["is_valid"] is False
    assert payload["profile"] == "lite"
    assert payload["errors"] == ["invalid_scope"]


def test_bridge_contracts_enforce_safety_assumptions() -> None:
    with pytest.raises(ValueError):
        ExecAdapterBridgeRequest(
            adapter_name="bad-adapter",
            adapter_type="BROKER_X",
            direction="outbound",
            payload={},
        )
    with pytest.raises(ValueError):
        ExecAdapterBridgeRequest(
            adapter_name="xtb-real-not-active",
            adapter_type="XTB",
            execution_venue="XTB",
            asset_class="STOCK",
            portfolio_bucket="FIRE_LONG_TERM",
            workflow="AUTO_REAL",
            direction="outbound",
            payload={},
        )
    with pytest.raises(ValueError):
        TelegramBridgeEnvelope(
            chat_id="chat-unsafe",
            sender_id="sender-unsafe",
            sender_role="operator",
            message_text="buy now",
            forbid_order_execution=False,
        )

    mt5_request = ExecAdapterBridgeRequest(
        adapter_name="mt5-forex-demo",
        adapter_type="MT5",
        execution_venue="MT5",
        asset_class="FOREX",
        portfolio_bucket="SHORT_TERM_TRADING",
        workflow="AUTO_DEMO",
        direction="outbound",
        payload={},
    )
    xtb_assisted = ExecAdapterBridgeRequest(
        adapter_name="xtb-assisted-etf",
        adapter_type="XTB",
        execution_venue="XTB",
        asset_class="ETF",
        portfolio_bucket="MEDIUM_TERM_3_5Y",
        workflow="TELEGRAM_ASSISTED",
        direction="outbound",
        payload={},
    )

    advisory = OpenAIAdvisoryRequest(
        advisory_context_ref="ctx-1",
        profile="full",
        question="summarize risk posture",
    )
    telegram = TelegramBridgeEnvelope(
        chat_id="chat-1",
        sender_id="sender-1",
        sender_role="operator",
        message_text="status",
    )

    assert advisory.forbid_order_execution is True
    assert advisory.forbid_state_mutation is True
    assert mt5_request.execution_venue == "MT5"
    assert mt5_request.workflow == "AUTO_DEMO"
    assert xtb_assisted.execution_venue == "XTB"
    assert xtb_assisted.workflow == "TELEGRAM_ASSISTED"
    assert telegram.forbid_order_execution is True
    assert telegram.enforce_via_command_gateway is True
    assert telegram.require_confirmation_for_critical is True
