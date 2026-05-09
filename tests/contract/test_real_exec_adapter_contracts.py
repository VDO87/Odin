from exec import RealExecutionAuditRecord, TransportSubmissionResult, TransportSubmissionStatus


def test_transport_submission_result_round_trip() -> None:
    result = TransportSubmissionResult(
        adapter_name="simulated_real",
        transport_status=TransportSubmissionStatus.ACCEPTED,
        external_order_ref="ord-1",
        accepted_price=1.1001,
        reason_summary="transport accepted",
        transport_metadata={"venue": "SIM-REAL"},
    )

    restored = TransportSubmissionResult.from_dict(result.to_dict())

    assert restored.adapter_name == "simulated_real"
    assert restored.transport_status == TransportSubmissionStatus.ACCEPTED
    assert restored.external_order_ref == "ord-1"
    assert restored.transport_metadata["venue"] == "SIM-REAL"


def test_real_execution_audit_record_round_trip() -> None:
    record = RealExecutionAuditRecord(
        intent_id="intent-1",
        request_id="request-1",
        adapter_name="simulated_real",
        operator_approval_ref="approval-1",
        approved_by="ops-admin",
        change_ticket="chg-real-1",
        transport_status="ACCEPTED",
        reason_summary="real execution confirmed",
        external_order_ref="ord-1",
        request_payload={"request_id": "request-1"},
        transport_payload={"external_order_ref": "ord-1"},
        snapshot_payload={"execution_state": "ES-70"},
        idempotency_payload={"status": "ES-70"},
    )

    restored = RealExecutionAuditRecord.from_dict(record.to_dict())

    assert restored.intent_id == "intent-1"
    assert restored.adapter_name == "simulated_real"
    assert restored.operator_approval_ref == "approval-1"
    assert restored.transport_payload["external_order_ref"] == "ord-1"
