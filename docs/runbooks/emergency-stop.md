# Emergency stop

Triggers: CPU/GPU >=80 C, CUDA/OOM, invalid data, unexpected flags, repeated network failure, secret exposure or suspected real account.

1. Do not contact broker. 2. Stop only the session process, do not delete state. 3. Preserve logs and record time/reason/process in D:\ODIN_LOCAL\reports. 4. Confirm safe_to_trade=false, real_trading=false and execution_allowed=false with smoke. 5. Revoke a leaked secret. Recover only through branch, tests and human review; never bypass a gate.
