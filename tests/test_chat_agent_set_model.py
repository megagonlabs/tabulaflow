from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from tabulaflow.app.session import create_workspace_connector
from tabulaflow.chat import ChatAgent
from tabulaflow.chat.agent import MAIN_REQUEST_TIMEOUT, SUBAGENT_REQUEST_TIMEOUT
from tabulaflow.core.db_connector.db_registry import DBRegistry


def test_activate_llm_profile_failure_is_transactional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = ChatAgent(registry=DBRegistry(), model="test", reasoning_effort="medium")
    runtime_agent = agent._pydantic_ai_agent
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        agent.activate_llm_profile(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning_effort="high",
            subagent_model=agent.subagent_model,
            subagent_reasoning_effort=agent.subagent_reasoning_effort,
        )
    # The failed switch left everything intact.
    assert agent.model == "test"
    assert agent.reasoning_effort == "medium"
    assert agent._pydantic_ai_agent is runtime_agent


def test_subagent_failure_does_not_partially_switch_main_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = ChatAgent(
        registry=DBRegistry(),
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning_effort="low",
    )
    runtime_agent = agent._pydantic_ai_agent

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        agent.activate_llm_profile(
            model="openai-responses:gpt-5.4-mini",
            reasoning_effort="high",
            subagent_model="anthropic:claude-sonnet-4-5-20250929",
            subagent_reasoning_effort="medium",
        )

    assert agent.model == "openai-responses:gpt-5"
    assert agent.reasoning_effort == "medium"
    assert agent.subagent_model == "openai-responses:gpt-5-mini"
    assert agent.subagent_reasoning_effort == "low"
    assert agent._pydantic_ai_agent is runtime_agent


def test_activate_llm_profile_preserves_conversation_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(
        registry=DBRegistry(),
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning_effort="low",
    )
    agent.note_event("remember this")
    message_history = agent._message_history
    query_history = agent.query_history
    tools = agent._tools
    runtime_agent = agent._pydantic_ai_agent

    keys = agent.activate_llm_profile(
        model="openai-responses:gpt-5.4-mini",
        reasoning_effort="high",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning_effort="medium",
    )

    assert agent._message_history is message_history
    assert agent.query_history is query_history
    assert agent._tools is tools
    assert agent._pydantic_ai_agent is not runtime_agent
    assert agent.model == "openai-responses:gpt-5.4-mini"
    assert agent.reasoning_effort == "high"
    assert agent.subagent_reasoning_effort == "medium"
    assert keys == ("sk-test123456789ab4x", "sk-test123456789ab4x")


def test_api_key_read_from_live_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(registry=DBRegistry(), model="openai-responses:gpt-5", reasoning_effort="medium")
    assert agent.resolve_api_keys() == ("sk-test123456789ab4x", "sk-test123456789ab4x")


def test_api_key_none_for_keyless_model() -> None:
    agent = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="medium",
        subagent_model="test",
    )
    assert agent.resolve_api_keys() == (None, None)


async def test_chat_agent_file_editor_is_unrestricted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    target = outside / "note.txt"
    target.write_text("outside content")
    monkeypatch.chdir(project)

    agent = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="medium",
        project_dir=project,
        scratch_dir=tmp_path / "scratch",
    )

    assert agent._tools.file_editor is not None
    out = await agent._tools.file_editor("view", str(target))
    assert "outside content" in out
    assert agent._tools.apply_patch is not None
    patch_out = await agent._tools.apply_patch(
        f"""*** Begin Patch
*** Update File: {target}
@@
-outside content
+edited outside
*** End Patch
"""
    )
    assert patch_out == f"M {target}"
    assert target.read_text() == "edited outside\n"


def test_chat_agent_file_editing_tools_follow_project_dir(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    without_project = ChatAgent(registry=DBRegistry(), model="test", reasoning_effort="medium")
    with_project = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="medium",
        project_dir=project,
    )

    assert without_project._tools.file_editor is None
    assert without_project._tools.apply_patch is None
    assert with_project._tools.file_editor is not None
    assert with_project._tools.apply_patch is not None


def test_chat_agent_tool_list_gates_apply_patch_to_gpt_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    project = tmp_path / "project"
    project.mkdir()

    without_project = ChatAgent(
        registry=DBRegistry(),
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
    )
    non_gpt = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="medium",
        project_dir=project,
    )
    openai_non_responses_gpt = ChatAgent(
        registry=DBRegistry(),
        model="openai-chat:gpt-5",
        reasoning_effort="medium",
        project_dir=project,
    )
    gpt = ChatAgent(
        registry=DBRegistry(),
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        project_dir=project,
    )

    without_tools = cast(Any, without_project._pydantic_ai_agent)._function_toolset.tools
    non_gpt_tools = cast(Any, non_gpt._pydantic_ai_agent)._function_toolset.tools
    openai_non_responses_gpt_tools = cast(Any, openai_non_responses_gpt._pydantic_ai_agent)._function_toolset.tools
    gpt_tools = cast(Any, gpt._pydantic_ai_agent)._function_toolset.tools
    assert "file_editor" not in without_tools
    assert "apply_patch" not in without_tools
    assert "file_editor" in non_gpt_tools
    assert "apply_patch" not in non_gpt_tools
    assert "file_editor" in openai_non_responses_gpt_tools
    assert "apply_patch" not in openai_non_responses_gpt_tools
    assert "file_editor" in gpt_tools
    assert "apply_patch" in gpt_tools


def test_chat_agent_apply_patch_tool_list_updates_on_model_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    project = tmp_path / "project"
    project.mkdir()
    agent = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="medium",
        project_dir=project,
    )

    initial_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "file_editor" in initial_tools
    assert "apply_patch" not in initial_tools

    agent.activate_llm_profile(
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning_effort=agent.subagent_reasoning_effort,
    )
    gpt_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "file_editor" in gpt_tools
    assert "apply_patch" in gpt_tools

    agent.activate_llm_profile(
        model="test",
        reasoning_effort="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning_effort=agent.subagent_reasoning_effort,
    )
    non_gpt_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "file_editor" in non_gpt_tools
    assert "apply_patch" not in non_gpt_tools


def _last_note(agent: ChatAgent) -> str:
    return cast(str, cast(Any, agent._message_history[-1]).parts[0].content)


def test_startup_note_states_model() -> None:
    agent = ChatAgent(registry=DBRegistry(), model="test", reasoning_effort="medium")
    assert len(agent._message_history) == 1
    assert _last_note(agent) == "[system: the model powering this conversation is test.]"


def test_activate_llm_profile_notes_model_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    project = tmp_path / "project"
    project.mkdir()
    agent = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="medium",
        project_dir=project,
    )

    agent.activate_llm_profile(
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning_effort=agent.subagent_reasoning_effort,
    )
    assert _last_note(agent) == (
        "[system: the model powering this conversation changed from test to "
        "openai-responses:gpt-5; the apply_patch tool is now available.]"
    )

    agent.activate_llm_profile(
        model="test",
        reasoning_effort="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning_effort=agent.subagent_reasoning_effort,
    )
    assert _last_note(agent) == (
        "[system: the model powering this conversation changed from "
        "openai-responses:gpt-5 to test; the apply_patch tool is no longer available.]"
    )

    # Effort- or subagent-only changes don't alter the main agent's context: no note.
    history_len = len(agent._message_history)
    agent.activate_llm_profile(
        model="test",
        reasoning_effort="high",
        subagent_model="openai-responses:gpt-5.4-mini",
        subagent_reasoning_effort="high",
    )
    assert len(agent._message_history) == history_len


def test_model_change_note_omits_apply_patch_without_file_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(registry=DBRegistry(), model="test", reasoning_effort="medium")

    agent.activate_llm_profile(
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning_effort=agent.subagent_reasoning_effort,
    )
    assert _last_note(agent) == (
        "[system: the model powering this conversation changed from test to openai-responses:gpt-5.]"
    )


def test_resolve_subagent_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-sub123456789cd9y")
    agent = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="medium",
        subagent_model="openai-responses:gpt-5.4-mini",
    )
    assert agent.resolve_api_keys() == (None, "sk-sub123456789cd9y")


def test_thinking_settings_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(registry=DBRegistry(), model="openai-responses:gpt-5", reasoning_effort="high")
    # Unified level plus OpenAI's reasoning summary; no max_tokens override for non-Anthropic models.
    assert agent._thinking_settings() == {
        "thinking": "high",
        "openai_reasoning_summary": "detailed",
        "timeout": MAIN_REQUEST_TIMEOUT,
    }


def test_service_tier_can_be_disabled_for_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(
        registry=DBRegistry(),
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        service_tier=None,
        subagent_model="openai-responses:gpt-5.4-mini",
    )
    assert agent._pydantic_ai_agent is not None
    assert agent._pydantic_ai_agent.model_settings == {}
    assert "openai_service_tier" not in agent._subagent_model_settings()


def test_thinking_settings_budget_era_claude_raises_max_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    agent = ChatAgent(registry=DBRegistry(), model="anthropic:claude-sonnet-4-5-20250929", reasoning_effort="high")
    settings = agent._thinking_settings()
    assert settings["thinking"] == "high"
    # sonnet-4-5 translates levels to budget_tokens (16384 for high); the API
    # requires max_tokens above the budget, and pydantic-ai's default is 4096.
    assert settings["max_tokens"] > 16384


def test_thinking_settings_adaptive_claude_no_max_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    agent = ChatAgent(registry=DBRegistry(), model="anthropic:claude-opus-4-8", reasoning_effort="high")
    # Adaptive-thinking models never use budgets — no max_tokens override.
    assert agent._thinking_settings() == {"thinking": "high", "timeout": MAIN_REQUEST_TIMEOUT}


def test_subagent_settings_budget_era_claude_raise_max_tokens() -> None:
    agent = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="low",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
        subagent_reasoning_effort="high",
    )
    assert agent._subagent_model_settings() == {
        "thinking": "high",
        "max_tokens": 24576,
        "timeout": SUBAGENT_REQUEST_TIMEOUT,
    }


async def test_subagent_profile_wires_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    workspace = await create_workspace_connector(tmp_path / "workspace.duckdb")
    try:
        agent = ChatAgent(
            registry=DBRegistry(),
            model="test",
            reasoning_effort="medium",
            workspace=workspace,
            subagent_model="anthropic:claude-opus-4-8",
            subagent_reasoning_effort="low",
        )
        assert agent._tools.run_subagent_for_each_row is not None
        assert agent._tools.extract_rows_from_documents is not None
        assert agent._tools.run_subagent_for_each_row.subagent_llm == "anthropic:claude-opus-4-8"
        assert agent._tools.extract_rows_from_documents.subagent_llm == "anthropic:claude-opus-4-8"
        assert agent._tools.add_canonical_name.subagent_llm == "anthropic:claude-opus-4-8"
        assert agent._tools.get_db_document.db_summarizer_llm == "anthropic:claude-opus-4-8"
        subagent_settings = {"thinking": "low", "timeout": SUBAGENT_REQUEST_TIMEOUT}
        assert agent._tools.run_subagent_for_each_row.model_settings == subagent_settings
        assert agent._tools.get_db_document.model_settings == subagent_settings

        agent._tools.get_db_document._document_cache["cached"] = cast(Any, (workspace, "old summary"))
        agent.activate_llm_profile(
            model=agent.model,
            reasoning_effort=agent.reasoning_effort,
            subagent_model="openai-responses:gpt-5.4-mini",
            subagent_reasoning_effort="high",
        )
        assert agent._tools.get_db_document._document_cache == {}
        assert agent._tools.run_subagent_for_each_row.subagent_llm == "openai-responses:gpt-5.4-mini"
        assert agent._tools.extract_rows_from_documents.subagent_llm == "openai-responses:gpt-5.4-mini"
        assert agent._tools.add_canonical_name.subagent_llm == "openai-responses:gpt-5.4-mini"
        assert agent._tools.get_db_document.db_summarizer_llm == "openai-responses:gpt-5.4-mini"
        settings = cast(dict[str, Any], agent._tools.run_subagent_for_each_row.model_settings)
        assert settings is not None
        assert settings["thinking"] == "high"
        assert settings["openai_reasoning_summary"] == "detailed"
        assert settings["openai_service_tier"] == "priority"
        settings = cast(dict[str, Any], agent._tools.extract_rows_from_documents.model_settings)
        assert settings["thinking"] == "high"
        assert settings["openai_reasoning_summary"] == "detailed"
        assert settings["openai_service_tier"] == "priority"
        settings = cast(dict[str, Any], agent._tools.add_canonical_name.model_settings)
        assert settings["thinking"] == "high"
        assert settings["openai_reasoning_summary"] == "detailed"
        assert settings["openai_service_tier"] == "priority"
        settings = cast(dict[str, Any], agent._tools.get_db_document.model_settings)
        assert settings["thinking"] == "high"
        assert settings["openai_reasoning_summary"] == "detailed"
        assert settings["openai_service_tier"] == "priority"
    finally:
        await workspace.disconnect_async()
