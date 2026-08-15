---
name: odin-data-provenance
description: Verify the origin, integrity, scope, and reproducibility of ODIN inputs, fixtures, datasets, logs, reports, metrics, and derived claims. Use whenever code or documentation relies on data whose source, timestamp, transformation, or authority could affect a decision or validation.
---

# ODIN Data Provenance

1. Identify source, owner or authority, retrieval time, scope, version/hash when available, and transformation steps.
2. Preserve raw evidence separately from derived output; label assumptions and unknowns.
3. Cross-check claims against the source or mark them unverified. Never invent data, provenance, test results, or telemetry.
4. Make transformations deterministic where practical and record the command or configuration needed to reproduce them.
5. Fail closed when provenance is missing for a safety-relevant conclusion; request the smallest needed evidence or human decision.

Do not treat simulated, demo, stale, partial, or manually edited data as authoritative without an explicit label.
