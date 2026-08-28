from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from tabulaflow.app import sample_data, session as session_module
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.session import AppSession
from tabulaflow.data.sql import SQLConnector


class _Workspace:
    global_id = "cli+workspace"

    def __init__(self) -> None:
        self.close_count = 0

    async def close_async(self) -> None:
        self.close_count += 1


@pytest.mark.asyncio
async def test_app_session_owns_runtime_creation_and_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = RuntimePaths.for_session("test-session", home_dir=tmp_path)
    workspace = _Workspace()
    created_paths: list[Path] = []
    sample_sessions: list[AppSession] = []

    async def create_workspace(path: Path) -> SQLConnector:
        created_paths.append(path)
        return cast(SQLConnector, workspace)

    async def connect_sample(session: AppSession) -> bool:
        sample_sessions.append(session)
        return True

    monkeypatch.setattr(session_module, "_warm_connector_imports", lambda: None)
    monkeypatch.setattr(session_module, "_create_workspace_connector", create_workspace)
    monkeypatch.setattr(sample_data, "autoconnect_sample", connect_sample)

    session = await AppSession.create(llm_preset=None, runtime_paths=paths, project_dir=tmp_path)

    assert created_paths == [paths.workspace_db_path]
    assert session.registry.list_aliases() == ["workspace"]
    assert sample_sessions == [session]
    assert paths.scratch_dir.is_dir()

    paths.scratch_dir.joinpath("intermediate.parquet").write_text("scratch")
    paths.data_dir.mkdir()
    paths.data_dir.joinpath("sales.duckdb").write_text("cache")
    paths.workspace_db_path.write_text("workspace")
    paths.logs_dir.mkdir()
    paths.logs_dir.joinpath("cli.log").write_text("log")
    paths.trajectories_dir.mkdir()
    paths.trajectories_dir.joinpath("trajectory.md").write_text("trajectory")

    await session.close()
    await session.close()

    assert workspace.close_count == 1
    assert not paths.scratch_dir.exists()
    assert not paths.data_dir.exists()
    assert paths.workspace_db_path.read_text() == "workspace"
    assert paths.cli_log_path.read_text() == "log"
    assert paths.trajectories_dir.joinpath("trajectory.md").read_text() == "trajectory"
