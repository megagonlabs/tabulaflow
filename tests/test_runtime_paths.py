from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from tabulaflow.app.runtime_paths import RuntimePaths, ensure_dumps_dir, prune_old_dumps


def test_dumps_dir_is_per_session_under_per_user_root() -> None:
    paths = RuntimePaths.for_session("sess-123")
    assert paths.dumps_dir.name == "sess-123"
    assert paths.dumps_dir.parent.name.startswith("tabulaflow")


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX directory permissions only")
def test_ensure_dumps_dir_locks_to_0700(tmp_path: Path) -> None:
    dumps_dir = tmp_path / "tabulaflow-test" / "sess-1"
    returned = ensure_dumps_dir(dumps_dir)
    assert returned == dumps_dir
    assert dumps_dir.is_dir()
    assert dumps_dir.stat().st_mode & 0o777 == 0o700
    assert dumps_dir.parent.stat().st_mode & 0o777 == 0o700


def test_prune_removes_old_session_dirs_keeps_recent(tmp_path: Path) -> None:
    old = tmp_path / "20200101T000000Z-1-abc"
    recent = tmp_path / "20990101T000000Z-2-def"
    old.mkdir()
    recent.mkdir()
    (old / "V_x.html").write_text("x")
    long_ago = time.time() - 30 * 86400
    os.utime(old, (long_ago, long_ago))

    prune_old_dumps(7 * 86400.0, root=tmp_path)

    assert not old.exists()
    assert recent.exists()
