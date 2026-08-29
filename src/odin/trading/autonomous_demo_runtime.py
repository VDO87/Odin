"""Local runtime helpers for the autonomous DEMO supervisor."""

from __future__ import annotations

from pathlib import Path
import re


_OBJECT_ID = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")
_SYMBOLIC_REF = re.compile(r"refs/[A-Za-z0-9._/-]+")


def read_local_git_checkpoint(repo_root: str | Path) -> str:
    """Read the current Git object id without starting Git or WSL processes.

    The persistent Windows supervisor runs directly from the repository exposed
    through the WSL UNC mount.  Reading Git's own metadata avoids making
    supervisor startup depend on a second WSL process while preserving a
    fail-closed checkpoint identity.
    """

    root = Path(repo_root)
    marker = root / ".git"
    git_dir = _resolve_git_directory(marker)
    head = _read_text(git_dir / "HEAD")
    if head.startswith("ref: "):
        ref = head.removeprefix("ref: ").strip()
        _validate_symbolic_ref(ref)
        object_id = _read_ref(git_dir, ref)
    else:
        object_id = head
    if _OBJECT_ID.fullmatch(object_id) is None:
        raise RuntimeError("git_checkpoint_invalid")
    return object_id[:7].lower()


def _resolve_git_directory(marker: Path) -> Path:
    if marker.is_dir():
        return marker
    value = _read_text(marker)
    if not value.startswith("gitdir: "):
        raise RuntimeError("git_directory_invalid")
    raw = value.removeprefix("gitdir: ").strip()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = marker.parent / candidate
    if not candidate.is_dir():
        raise RuntimeError("git_directory_unavailable")
    return candidate


def _read_ref(git_dir: Path, ref: str) -> str:
    loose = git_dir.joinpath(*ref.split("/"))
    if loose.is_file():
        return _read_text(loose)
    packed_roots = [git_dir]
    commondir = git_dir / "commondir"
    if commondir.is_file():
        raw = _read_text(commondir)
        common = Path(raw)
        if not common.is_absolute():
            common = git_dir / common
        packed_roots.append(common)
    for root in packed_roots:
        packed = root / "packed-refs"
        if not packed.is_file():
            continue
        for line in packed.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith(("#", "^")):
                continue
            object_id, separator, packed_ref = line.partition(" ")
            if separator and packed_ref == ref:
                return object_id
    raise RuntimeError("git_checkpoint_unavailable")


def _validate_symbolic_ref(ref: str) -> None:
    if (
        _SYMBOLIC_REF.fullmatch(ref) is None
        or ".." in ref
        or "//" in ref
        or ref.endswith(("/", ".lock"))
    ):
        raise RuntimeError("git_symbolic_ref_invalid")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RuntimeError("git_metadata_unavailable") from error
