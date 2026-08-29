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
    ids = iter(("k3x9qe", "p07mzt"))
    monkeypatch.setattr(runtime_paths, "generate_session_id", lambda: next(ids))
    home_dir = tmp_path / ".tabulaflow"
    existing = RuntimePaths.for_session("k3x9qe", home_dir=home_dir).session_dir
    existing.mkdir(parents=True)

    paths = RuntimePaths.create(home_dir=home_dir)

    assert paths.session_id == "p07mzt"
    assert paths.session_dir.is_dir()


def test_runtime_paths_are_derived_from_app_and_session(tmp_path: Path) -> None:
    paths = RuntimePaths.for_session("sess-123", home_dir=tmp_path)
    assert paths.session_id == "sess-123"
    assert paths.session_dir == tmp_path / "sessions" / "sess-123"
    assert paths.logs_dir == paths.session_dir / "logs"
    assert paths.trajectories_dir == paths.session_dir / "trajectories"
    assert paths.data_dir == paths.session_dir / "data"
    assert paths.scratch_dir == paths.session_dir / "scratch"
    assert paths.workspace_db_path == paths.session_dir / "workspace.duckdb"
    assert paths.pane_dir == paths.session_dir / "pane"
    assert paths.history_path == tmp_path / "history.jsonl"
    assert paths.cli_log_path == paths.logs_dir / "cli.log"


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX directory permissions only")
def test_ensure_pane_dir_locks_to_0700(tmp_path: Path) -> None:
    pane_dir = tmp_path / "tabulaflow-test" / "sess-1"
    returned = ensure_pane_dir(pane_dir)
    assert returned == pane_dir
    assert pane_dir.is_dir()
    assert pane_dir.stat().st_mode & 0o777 == 0o700
    assert pane_dir.parent.stat().st_mode & 0o777 == 0o700
