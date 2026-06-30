from __future__ import annotations

import os
from pathlib import Path

import pytest

from tabulaflow.app.runtime_paths import RuntimePaths, ensure_pane_dir


def test_pane_dir_is_durable_under_session() -> None:
    paths = RuntimePaths.for_session("sess-123")
    assert paths.pane_dir.name == "pane"
    assert paths.pane_dir.parent.name == "sess-123"
    assert paths.pane_dir.parent.parent.name == "sessions"


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX directory permissions only")
def test_ensure_pane_dir_locks_to_0700(tmp_path: Path) -> None:
    pane_dir = tmp_path / "tabulaflow-test" / "sess-1"
    returned = ensure_pane_dir(pane_dir)
    assert returned == pane_dir
    assert pane_dir.is_dir()
    assert pane_dir.stat().st_mode & 0o777 == 0o700
    assert pane_dir.parent.stat().st_mode & 0o777 == 0o700
