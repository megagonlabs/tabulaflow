from __future__ import annotations

import os
from pathlib import Path
import re

import pytest

from tabulaflow.app import runtime_paths
from tabulaflow.app.runtime_paths import RuntimePaths, ensure_pane_dir, generate_session_id


def test_generate_session_id_is_short_lowercase_base36() -> None:
    assert re.fullmatch(r"[0-9a-z]{6}", generate_session_id())


def test_create_runtime_paths_retries_id_collision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    ids = iter(("k3x9qe", "p07mzt"))
    monkeypatch.setattr(runtime_paths, "generate_session_id", lambda: next(ids))
    existing = RuntimePaths.for_session("k3x9qe").pane_dir.parent
    existing.mkdir(parents=True)

    paths = RuntimePaths.create()

    assert paths.pane_dir.parent.name == "p07mzt"
    assert paths.pane_dir.parent.is_dir()


def test_pane_dir_is_scoped_to_session() -> None:
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
