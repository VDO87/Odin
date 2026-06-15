"""Import shim for running ``python -m odin.cli`` from the repository root."""

from __future__ import annotations

from pathlib import Path

_SRC_ODIN = Path(__file__).resolve().parent.parent / "src" / "odin"
if _SRC_ODIN.exists():
    __path__.append(str(_SRC_ODIN))

