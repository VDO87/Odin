# ODIN RC1.5 Soak Test Result

- Started at: `2026-05-09T19:08:05.800901+00:00`
- Finished at: `2026-05-09T19:08:11.233898+00:00`
- Duration seconds: `5.43`
- Result: `PASS`

## Summary
- Total cycles: `8`
- Successful cycles: `8`
- Failed cycles: `0`
- Max cycle duration ms: `504.99`
- Avg cycle duration ms: `427.91`
- Total errors: `0`
- Heartbeat valid: `True`
- Snapshot valid: `True`
- Events valid: `True`
- No order attempts: `True`
- Safety flags OK: `True`

## Dangerous Commands
- `ENABLE_REAL_TRADING` -> accepted=`False` reason=`dangerous_command_blocked`
- `MT5_ORDER_SEND` -> accepted=`False` reason=`dangerous_command_blocked`
- `DIRECT_ORDER_SEND` -> accepted=`False` reason=`dangerous_command_blocked`
- `BROKER_REAL_EXECUTION` -> accepted=`False` reason=`dangerous_command_blocked`

## Errors
- none

## Last Cycle
- cycle_number: `8`
- timestamp: `2026-05-09T19:08:10.634616+00:00`
- duration_ms: `416.36`
- runtime_state: `RUNNING`
- safe_to_trade: `False`
- health_status: `UNKNOWN`
- heartbeat_written: `True`
- snapshot_written: `True`
- event_count: `3911`
- mt5_status: `UNKNOWN`
- llm_status: `UNKNOWN`
- atlas_status: `UNKNOWN`
- order_attempt_detected: `False`
