from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from tabulaflow.app import sample_data, session as session_module
from tabulaflow.agents.llm import ReasoningLevel
from tabulaflow.app.config import LLMRoleConfig, LLMPreset
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.session import AppSession
from tabulaflow.data.sql import SQLConnector

if TYPE_CHECKING:
    from tabulaflow.agents.chat import ChatSession


class _Workspace:
    global_id = "cli+workspace"

    def __init__(self) -> None:
        self.close_count = 0

    async def close_async(self) -> None:
        self.close_count += 1


def _preset(
    *,
    model: str = "test",
    reasoning: ReasoningLevel = "low",
    subagent_model: str = "test",
    subagent_reasoning: ReasoningLevel = "medium",
) -> LLMPreset:
    return LLMPreset(
        label="Test",
        main=LLMRoleConfig(model=model, reasoning=reasoning),
        subagent=LLMRoleConfig(model=subagent_model, reasoning=subagent_reasoning),
    )


def _session(*, llm_preset: LLMPreset | None, tmp_path: Path) -> AppSession:
    return AppSession(
        llm_preset=llm_preset,
        runtime_paths=RuntimePaths.for_session("test-session", home_dir=tmp_path),
        workspace=None,
    )


def _activate_selected(session: AppSession) -> ChatSession:
    assert session.selected_preset is not None
    session.activate_llm_preset(session.selected_preset)
    agent = session.active_chat_session
    assert agent is not None
    return agent


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


def test_reset_conversation_preserves_session_environment(tmp_path: Path) -> None:
    session = _session(
        llm_preset=_preset(),
        tmp_path=tmp_path,
    )
    agent = _activate_selected(session)
    initial_history = list(agent._message_history)
    output_store = agent.output_store
    agent.note_event("old conversation detail")

    session.reset_conversation()

    assert session.active_chat_session is agent
    assert len(agent._message_history) == len(initial_history)
    reset_part: Any = agent._message_history[0].parts[0]
    initial_part: Any = initial_history[0].parts[0]
    assert reset_part.content == initial_part.content
    assert agent.output_store is output_store
    assert agent._registry is session.registry


def test_session_starts_with_unverified_llm_preset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    session = _session(
        llm_preset=_preset(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning="medium",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
            subagent_reasoning="medium",
        ),
        tmp_path=tmp_path,
    )

    assert session.active_chat_session is None
    assert session.selected_preset is not None
    assert session.selected_preset.main.model == "anthropic:claude-sonnet-4-5-20250929"
    assert session.registry.list_aliases() == []
    session.note_event("ignored without an LLM")

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        _activate_selected(session)
    assert session.active_chat_session is None


def test_initial_activation_requires_subagent_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = _session(
        llm_preset=_preset(
            model="test",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
        ),
        tmp_path=tmp_path,
    )

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        _activate_selected(session)
    assert session.active_chat_session is None


def test_session_starts_without_llm_preset(tmp_path: Path) -> None:
    session = _session(
        llm_preset=None,
        tmp_path=tmp_path,
    )

    assert session.selected_preset is None
    assert session.active_chat_session is None


def test_llm_off_keeps_initialized_agent_dormant(tmp_path: Path) -> None:
    preset = _preset()
    session = _session(
        llm_preset=preset,
        tmp_path=tmp_path,
    )
    agent = _activate_selected(session)

    session.select_llm_preset(None)

    assert session.selected_preset is None
    assert session.active_chat_session is None
    session.select_llm_preset(preset)
    assert session.active_chat_session is agent


def test_unverified_session_can_select_and_then_build_valid_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = _session(
        llm_preset=_preset(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning="medium",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
            subagent_reasoning="medium",
        ),
        tmp_path=tmp_path,
    )

    session.select_llm_preset(_preset())
    session.activate_llm_preset(_preset())

    assert session.selected_preset == _preset()
    assert session.active_chat_session is not None


def test_selecting_unusable_preset_defers_error_until_agent_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = _session(
        llm_preset=_preset(),
        tmp_path=tmp_path,
    )
    old_agent = _activate_selected(session)
    old_model = old_agent.model

    selected_preset = _preset(
        model="anthropic:claude-sonnet-4-5-20250929",
        reasoning="medium",
        subagent_model="anthropic:claude-haiku-4-5-20251001",
        subagent_reasoning="medium",
    )
    session.select_llm_preset(selected_preset)
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        session.activate_llm_preset(selected_preset)
    assert session.selected_preset == selected_preset
    assert session.active_chat_session is None
    assert old_agent.model == old_model
    session.select_llm_preset(_preset())
    assert session.active_chat_session is old_agent


def test_switching_preset_preserves_live_chat_session_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    session = _session(
        llm_preset=_preset(
            model="openai-responses:gpt-5",
            reasoning="medium",
            subagent_model="openai-responses:gpt-5-mini",
            subagent_reasoning="low",
        ),
        tmp_path=tmp_path,
    )
    agent = _activate_selected(session)
    agent.note_event("remember this")
    message_history = agent._message_history
    output_store = agent.output_store

    selected_preset = _preset(
        model="openai-responses:gpt-5.4-mini",
        reasoning="high",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning="medium",
    )
    session.select_llm_preset(selected_preset)
    session.activate_llm_preset(selected_preset)

    assert session.active_chat_session is agent
    assert agent.resolve_api_keys()[0] == "sk-test123456789ab4x"
    assert agent._message_history is message_history
    assert agent.output_store is output_store
