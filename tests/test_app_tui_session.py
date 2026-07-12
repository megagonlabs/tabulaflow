from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tabulaflow.app import session as session_module
from tabulaflow.app import tui
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.tui import TabulaflowApp


@pytest.mark.asyncio
async def test_ensure_session_passes_session_paths_by_keyword(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.chdir(project_dir)

    app = TabulaflowApp(
        model="test:model",
        reasoning_effort="low",
        subagent_model="test:subagent",
        subagent_reasoning_effort="medium",
    )
    runtime_paths = RuntimePaths.for_session("test-session")
    app._runtime_paths = runtime_paths

    workspace = object()
    session = object()
    captured: dict[str, Any] = {}

    async def fake_create_workspace_connector(workspace_db_path: Path) -> object:
        captured["workspace_db_path"] = workspace_db_path
        return workspace

    def fake_session_state(**kwargs: Any) -> object:
        captured["session_kwargs"] = kwargs
        return session

    async def fake_autoconnect_sample(_session: object) -> None:
        captured["autoconnect_session"] = _session

    monkeypatch.setattr(session_module, "create_workspace_connector", fake_create_workspace_connector)
    monkeypatch.setattr(tui, "_warm_session_imports", lambda: None)
    monkeypatch.setattr(tui, "SessionState", fake_session_state)
    monkeypatch.setattr(app, "_maybe_autoconnect_sample", fake_autoconnect_sample)
    monkeypatch.setattr(app, "_enable_explorer_button", lambda: None)

    result = await app._ensure_session()

    assert result is session
    assert captured["workspace_db_path"] == runtime_paths.workspace_db_path
    assert captured["autoconnect_session"] is session
    assert captured["session_kwargs"] == {
        "model": "test:model",
        "session_id": app._session_id,
        "trajectories_dir": runtime_paths.trajectories_dir,
        "data_dir": runtime_paths.data_dir,
        "workspace": workspace,
        "reasoning_effort": "low",
        "project_dir": project_dir,
        "scratch_dir": runtime_paths.scratch_dir,
        "subagent_model": "test:subagent",
        "subagent_reasoning_effort": "medium",
    }
