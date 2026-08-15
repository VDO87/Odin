# ODIN Baseline Soak Report

**Date:** 2026-08-15 20:40 UTC  
**Baseline:** `9f1df38` (immutable parent)  
**Branch under observation:** `feature/shadow-intelligence-rc1`

## Method

One bounded, supervised refresh was run through the approved Windows launcher
with MT5 timeout 10 s and public-data timeout 30 s. The run used no order path,
no credential changes and no persistent daemon.

## Observed result

- MT5 DEMO: `CONNECTED_DEMO_READ_ONLY`, zero positions, content hash persisted.
- Public source: ECB EXR returned `OK`; duplicate evidence was identified rather
  than silently rewritten.
- Shadow observation: fresh MT5/public inputs, `OBSERVED_NO_DECISION`.
- Hermes: `LOCAL_ONLY`, `OK`; Ollama `qwen2.5-coder:1.5b` available.
- Cockpit operational report: `OK`; observer remained disabled.
- Guardrails: `safe_to_trade=false`, `real_trading=false`,
  `execution_allowed=false` throughout.

## Resource and stability sample

| Measure | Observation |
|---|---|
| WSL RAM available | 5,511–5,551 MiB / 5,926 MiB |
| WSL swap used | 0 MiB / 6,144 MiB |
| WSL disk free | 953.13 GiB |
| GPU | Quadro M4000, 40°C, 0 MiB/8,192 MiB, 0% utilisation |
| MT5 terminal processes | 2; no process was terminated |
| WSL logs/runtime size before refresh | 61 MiB / 52 MiB |
| Refresh completion | 26.2 s; no crash or exception |

## Conclusion

The bounded supervised soak sample is stable and persisted its evidence. It is
not evidence for trading authority: the baseline remains read-only and the
Shadow RC may only consume the resulting observations and validated P0 data.
