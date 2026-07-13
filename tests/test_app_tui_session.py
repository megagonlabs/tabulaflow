from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tabulaflow.app import session as session_module
from tabulaflow.app import tui
from tabulaflow.app.config import LLMRoleConfig, LLMPreset, ReasoningEffort
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.session import SessionState
from tabulaflow.app.tui import TabulaflowApp


class _StatusCapture:
    def __init__(self) -> None:
        self.value = ""

    def update(self, value: object) -> None:
        self.value = str(value)


def _preset(
    *,
    label: str = "Test",
    model: str = "test",
    reasoning_effort: ReasoningEffort = "low",
    subagent_model: str = "test",
    subagent_reasoning_effort: ReasoningEffort = "medium",
) -> LLMPreset:
    return LLMPreset(
        label=label,
        main=LLMRoleConfig(model=model, reasoning_effort=reasoning_effort),
        subagent=LLMRoleConfig(model=subagent_model, reasoning_effort=subagent_reasoning_effort),
    )


@pytest.mark.asyncio
async def test_ensure_session_passes_session_paths_by_keyword(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.chdir(project_dir)

    preset = _preset(model="test:model", subagent_model="test:subagent")
    app = TabulaflowApp(
        llm_preset=preset,
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
        "llm_preset": preset,
        "session_id": app._session_id,
        "trajectories_dir": runtime_paths.trajectories_dir,
        "data_dir": runtime_paths.data_dir,
        "workspace": workspace,
        "project_dir": project_dir,
        "scratch_dir": runtime_paths.scratch_dir,
    }


def test_bottom_status_shows_selected_model_before_agent_is_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset = _preset(
        model="anthropic:claude-opus-4-8",
        reasoning_effort="high",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
    )
    app = TabulaflowApp(llm_preset=preset)
    app._project_dir = tmp_path
    session = SessionState(
        llm_preset=preset,
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    session.chat_agent = None
    app._session = session
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)

    app._refresh_bottom_status()

    assert model_status.value.startswith("Opus 4.8 high · ")


def test_bottom_status_shows_startup_model_before_session_is_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = TabulaflowApp(
        llm_preset=_preset(
            model="anthropic:claude-opus-4-8",
            reasoning_effort="high",
            subagent_model="anthropic:claude-sonnet-4-5-20250929",
        )
    )
    app._project_dir = tmp_path
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)

    app._refresh_bottom_status()

    assert model_status.value.startswith("Opus 4.8 high · ")


def test_bottom_status_shows_llm_off_before_session_when_no_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = TabulaflowApp(llm_preset=None)
    app._project_dir = tmp_path
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)

    app._refresh_bottom_status()

    assert model_status.value.startswith("LLM off · ")


def test_session_starts_with_unverified_llm_preset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    session = SessionState(
        llm_preset=_preset(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning_effort="medium",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
            subagent_reasoning_effort="medium",
        ),
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    assert session.chat_agent is None
    assert not session.llm_available
    assert session.llm_error is None
    assert session.model == "anthropic:claude-sonnet-4-5-20250929"
    assert session.registry.list_aliases() == []
    session.note_event("ignored without an LLM")

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        session.ensure_chat_agent()
    assert session.chat_agent is None
    assert session.llm_error is not None
    assert "ANTHROPIC_API_KEY" in session.llm_error


def test_session_starts_without_llm_preset(tmp_path: Path) -> None:
    session = SessionState(
        llm_preset=None,
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    assert session.llm_preset is None
    assert session.chat_agent is None
    assert not session.llm_available
    assert session.llm_error is None
    with pytest.raises(RuntimeError, match="No LLM preset"):
        _ = session.model


def test_unverified_session_can_select_and_then_build_valid_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = SessionState(
        llm_preset=_preset(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning_effort="medium",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
            subagent_reasoning_effort="medium",
        ),
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    session.set_llm_preset(_preset())

    assert not session.llm_available
    assert session.llm_error is None
    assert session.chat_agent is None
    assert session.model == "test"
    assert session.reasoning_effort == "low"
    assert session.subagent_model == "test"
    assert session.subagent_reasoning_effort == "medium"

    session.ensure_chat_agent()
    assert session.llm_available
    assert session.llm_error is None
    assert session.chat_agent is not None


def test_selecting_unusable_preset_defers_error_until_agent_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = SessionState(
        llm_preset=_preset(),
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    old_agent = session.ensure_chat_agent()
    old_model = old_agent.model

    session.set_llm_preset(
        _preset(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning_effort="medium",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
            subagent_reasoning_effort="medium",
        )
    )

    assert session.llm_error is None
    assert session.chat_agent is old_agent
    assert not session.llm_available
    assert session.model == "anthropic:claude-sonnet-4-5-20250929"
    assert session.reasoning_effort == "medium"
    assert session.subagent_model == "anthropic:claude-haiku-4-5-20251001"
    assert session.subagent_reasoning_effort == "medium"

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        session.ensure_chat_agent()
    assert session.chat_agent is old_agent
    assert old_agent.model == old_model
    assert session.llm_error is not None


def test_switching_preset_preserves_live_chat_agent_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    session = SessionState(
        llm_preset=_preset(
            model="openai-responses:gpt-5",
            reasoning_effort="medium",
            subagent_model="openai-responses:gpt-5-mini",
            subagent_reasoning_effort="low",
        ),
        session_id="test-session",
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    agent = session.ensure_chat_agent()
    agent.note_event("remember this")
    message_history = agent._message_history
    query_history = agent.query_history

    session.set_llm_preset(
        _preset(
            model="openai-responses:gpt-5.4-mini",
            reasoning_effort="high",
            subagent_model="openai-responses:gpt-5-mini",
            subagent_reasoning_effort="medium",
        )
    )

    assert session.chat_agent is agent
    assert not session.llm_available
    assert session.api_key is None
    assert session.ensure_chat_agent() is agent
    assert session.llm_available
    assert session.api_key == "sk-test123456789ab4x"
    assert agent._message_history is message_history
    assert agent.query_history is query_history
