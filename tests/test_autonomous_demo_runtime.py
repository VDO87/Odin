from __future__ import annotations

from pathlib import Path

import pytest

from odin.trading.autonomous_demo_runtime import read_local_git_checkpoint


def _write_repository(root: Path, *, head: str, refs: dict[str, str] | None = None) -> None:
    git_dir = root / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text(head, encoding="utf-8")
    for ref, object_id in (refs or {}).items():
        path = git_dir.joinpath(*ref.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(object_id, encoding="utf-8")


def test_reads_loose_symbolic_ref_without_process_lookup(tmp_path: Path) -> None:
    object_id = "8aafea2c75a5059457e6d0d13e8d6772a1ef739b"
    _write_repository(
        tmp_path,
        head="ref: refs/heads/feature/autonomous-demo-operations-rc2\n",
        refs={"refs/heads/feature/autonomous-demo-operations-rc2": object_id},
    )

    assert read_local_git_checkpoint(tmp_path) == "8aafea2"


def test_reads_detached_head(tmp_path: Path) -> None:
    _write_repository(
        tmp_path,
        head="3418d8b012345678901234567890123456789012\n",
    )

    assert read_local_git_checkpoint(tmp_path) == "3418d8b"


def test_reads_packed_ref(tmp_path: Path) -> None:
    object_id = "8528df9012345678901234567890123456789012"
    _write_repository(tmp_path, head="ref: refs/heads/packed\n")
    (tmp_path / ".git" / "packed-refs").write_text(
        f"# pack-refs with: peeled fully-peeled\n{object_id} refs/heads/packed\n",
        encoding="utf-8",
    )

    assert read_local_git_checkpoint(tmp_path) == "8528df9"


@pytest.mark.parametrize(
    "head",
    [
        "not-an-object-id\n",
        "ref: ../../outside\n",
        "ref: refs/heads/../outside\n",
    ],
)
def test_invalid_or_unsafe_metadata_fails_closed(tmp_path: Path, head: str) -> None:
    _write_repository(tmp_path, head=head)

    with pytest.raises(RuntimeError):
        read_local_git_checkpoint(tmp_path)
