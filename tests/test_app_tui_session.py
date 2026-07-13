from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tabulaflow.app import session as session_module
from tabulaflow.app import tui
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.session import ActiveLLMProfile, SessionState
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


def test_session_starts_when_llm_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    session = SessionState(
        model="anthropic:claude-sonnet-4-5-20250929",
        reasoning_effort="medium",
        subagent_model="anthropic:claude-haiku-4-5-20251001",
        subagent_reasoning_effort="medium",
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    assert session.chat_agent is None
    assert not session.llm_available
    assert session.llm_error is not None
    assert "ANTHROPIC_API_KEY" in session.llm_error
    assert session.model == "anthropic:claude-sonnet-4-5-20250929"
    assert session.registry.list_aliases() == []
    session.note_event("ignored without an LLM")


def test_unavailable_session_can_switch_to_valid_llm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = SessionState(
        model="anthropic:claude-sonnet-4-5-20250929",
        reasoning_effort="medium",
        subagent_model="anthropic:claude-haiku-4-5-20251001",
        subagent_reasoning_effort="medium",
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    session.set_llm_profile(
        ActiveLLMProfile.from_values(
            model="test",
            reasoning_effort="low",
            subagent_model="test",
            subagent_reasoning_effort="medium",
        )
    )

    assert session.llm_available
    assert session.llm_error is None
    assert session.chat_agent is not None
    assert session.model == "test"
    assert session.reasoning_effort == "low"
    assert session.subagent_model == "test"
    assert session.subagent_reasoning_effort == "medium"


def test_invalid_profile_switch_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = SessionState(
        model="test",
        reasoning_effort="low",
        subagent_model="test",
        subagent_reasoning_effort="medium",
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    old_agent = session.chat_agent

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        session.set_llm_profile(
            ActiveLLMProfile.from_values(
                model="anthropic:claude-sonnet-4-5-20250929",
                reasoning_effort="medium",
                subagent_model="anthropic:claude-haiku-4-5-20251001",
                subagent_reasoning_effort="medium",
            )
        )

    assert session.chat_agent is old_agent
    assert session.llm_available
    assert session.llm_error is None
    assert session.model == "test"
    assert session.reasoning_effort == "low"
    assert session.subagent_model == "test"
    assert session.subagent_reasoning_effort == "medium"
