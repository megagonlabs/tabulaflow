from __future__ import annotations

from pathlib import Path
import inspect
from typing import Any, cast

import pytest

from tabulaflow.app.session import _create_workspace_connector
from tabulaflow.agents.chat import ChatSession
from tabulaflow.agents.chat.session import MAIN_REQUEST_TIMEOUT, SUBAGENT_REQUEST_TIMEOUT
from tabulaflow.data.registry import DataConnectorRegistry


def test_chat_session_constructor_is_keyword_only_and_state_is_read_only() -> None:
    signature = inspect.signature(ChatSession)
    assert signature.parameters["model"].kind is inspect.Parameter.KEYWORD_ONLY
    assert "last_usage" not in signature.parameters

    agent = ChatSession(registry=DataConnectorRegistry(), model="test", reasoning="medium")
    with pytest.raises(AttributeError):
        agent.model = "other"  # type: ignore[misc]


def test_activate_llm_profile_failure_is_transactional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = ChatSession(registry=DataConnectorRegistry(), model="test", reasoning="medium")
    runtime_agent = agent._pydantic_ai_agent
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        agent.activate_llm_profile(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning="high",
            subagent_model=agent.subagent_model,
            subagent_reasoning=agent.subagent_reasoning,
            use_apply_patch=agent.use_apply_patch,
        )
    # The failed switch left everything intact.
    assert agent.model == "test"
    assert agent.reasoning == "medium"
    assert agent._pydantic_ai_agent is runtime_agent


def test_subagent_failure_does_not_partially_switch_main_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="openai-responses:gpt-5",
        reasoning="medium",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning="low",
    )
    runtime_agent = agent._pydantic_ai_agent

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        agent.activate_llm_profile(
            model="openai-responses:gpt-5.4-mini",
            reasoning="high",
            subagent_model="anthropic:claude-sonnet-4-5-20250929",
            subagent_reasoning="medium",
            use_apply_patch=agent.use_apply_patch,
        )

    assert agent.model == "openai-responses:gpt-5"
    assert agent.reasoning == "medium"
    assert agent.subagent_model == "openai-responses:gpt-5-mini"
    assert agent.subagent_reasoning == "low"
    assert agent._pydantic_ai_agent is runtime_agent


def test_activate_llm_profile_preserves_conversation_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="openai-responses:gpt-5",
        reasoning="medium",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning="low",
    )
    agent.note_event("remember this")
    message_history = agent._context_messages
    output_store = agent.output_store
    tools = agent._tools
    runtime_agent = agent._pydantic_ai_agent

    keys = agent.activate_llm_profile(
        model="openai-responses:gpt-5.4-mini",
        reasoning="high",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning="medium",
        use_apply_patch=agent.use_apply_patch,
    )

    assert agent._context_messages is message_history
    assert agent.output_store is output_store
    assert agent._tools is tools
    assert agent._pydantic_ai_agent is not runtime_agent
    assert agent.model == "openai-responses:gpt-5.4-mini"
    assert agent.reasoning == "high"
    assert agent.subagent_reasoning == "medium"
    assert keys == ("sk-test123456789ab4x", "sk-test123456789ab4x")


def test_api_key_read_from_live_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatSession(registry=DataConnectorRegistry(), model="openai-responses:gpt-5", reasoning="medium")
    assert agent.resolve_api_keys() == ("sk-test123456789ab4x", "sk-test123456789ab4x")


def test_api_key_none_for_keyless_model() -> None:
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        subagent_model="test",
    )
    assert agent.resolve_api_keys() == (None, None)


async def test_chat_session_file_tools_are_unrestricted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    target = outside / "note.txt"
    target.write_text("outside content")
    monkeypatch.chdir(project)

    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        project_dir=project,
        scratch_dir=tmp_path / "scratch",
    )

    assert agent._tools.view is not None
    out = await agent._tools.view(str(target))
    assert isinstance(out, str)
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


def test_chat_session_file_editing_tools_follow_project_dir(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    without_project = ChatSession(registry=DataConnectorRegistry(), model="test", reasoning="medium")
    with_project = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        project_dir=project,
    )

    assert without_project._tools.view is None
    assert without_project._tools.edit_file is None
    assert without_project._tools.apply_patch is None
    assert with_project._tools.view is not None
    assert with_project._tools.edit_file is not None
    assert with_project._tools.apply_patch is not None


def test_chat_session_tool_list_includes_file_tools_for_every_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    project = tmp_path / "project"
    project.mkdir()

    without_project = ChatSession(
        registry=DataConnectorRegistry(),
        model="openai-responses:gpt-5",
        reasoning="medium",
    )
    non_gpt = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        project_dir=project,
        use_apply_patch=True,
    )
    openai_non_responses_gpt = ChatSession(
        registry=DataConnectorRegistry(),
        model="openai-chat:gpt-5",
        reasoning="medium",
        project_dir=project,
        use_apply_patch=True,
    )
    gpt = ChatSession(
        registry=DataConnectorRegistry(),
        model="openai-responses:gpt-5",
        reasoning="medium",
        project_dir=project,
        use_apply_patch=True,
    )

    without_tools = cast(Any, without_project._pydantic_ai_agent)._function_toolset.tools
    non_gpt_tools = cast(Any, non_gpt._pydantic_ai_agent)._function_toolset.tools
    openai_non_responses_gpt_tools = cast(Any, openai_non_responses_gpt._pydantic_ai_agent)._function_toolset.tools
    gpt_tools = cast(Any, gpt._pydantic_ai_agent)._function_toolset.tools
    assert "view" not in without_tools
    assert "edit_file" not in without_tools
    assert "apply_patch" not in without_tools
    assert "view" in non_gpt_tools
    assert "edit_file" not in non_gpt_tools
    assert "apply_patch" in non_gpt_tools
    assert "view" in openai_non_responses_gpt_tools
    assert "edit_file" not in openai_non_responses_gpt_tools
    assert "apply_patch" in openai_non_responses_gpt_tools
    assert "view" in gpt_tools
    assert "edit_file" not in gpt_tools
    assert "apply_patch" in gpt_tools


def test_chat_session_file_tool_list_is_stable_across_model_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    project = tmp_path / "project"
    project.mkdir()
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        project_dir=project,
        use_apply_patch=True,
    )

    initial_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "view" in initial_tools
    assert "edit_file" not in initial_tools
    assert "apply_patch" in initial_tools

    agent.activate_llm_profile(
        model="openai-responses:gpt-5",
        reasoning="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning=agent.subagent_reasoning,
        use_apply_patch=agent.use_apply_patch,
    )
    gpt_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "view" in gpt_tools
    assert "edit_file" not in gpt_tools
    assert "apply_patch" in gpt_tools

    agent.activate_llm_profile(
        model="test",
        reasoning="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning=agent.subagent_reasoning,
        use_apply_patch=agent.use_apply_patch,
    )
    non_gpt_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "view" in non_gpt_tools
    assert "edit_file" not in non_gpt_tools
    assert "apply_patch" in non_gpt_tools


def test_apply_patch_capability_controls_tool_schema(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        project_dir=project,
    )

    initial_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "view" in initial_tools
    assert "edit_file" in initial_tools
    assert "apply_patch" not in initial_tools

    agent.activate_llm_profile(
        model="test",
        reasoning="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning=agent.subagent_reasoning,
        use_apply_patch=True,
    )
    enabled_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "apply_patch" in enabled_tools
    assert "edit_file" not in enabled_tools
    assert _last_note(agent) == "[system: apply_patch is now available and replaces edit_file.]"

    agent.activate_llm_profile(
        model="test",
        reasoning="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning=agent.subagent_reasoning,
        use_apply_patch=False,
    )
    disabled_tools = cast(Any, agent._pydantic_ai_agent)._function_toolset.tools
    assert "apply_patch" not in disabled_tools
    assert "edit_file" in disabled_tools
    assert _last_note(agent) == "[system: edit_file is now available and replaces apply_patch.]"


def _last_note(agent: ChatSession) -> str:
    return cast(str, cast(Any, agent._context_messages[-1]).parts[0].content)


def test_startup_note_states_model() -> None:
    agent = ChatSession(registry=DataConnectorRegistry(), model="test", reasoning="medium")
    assert len(agent._context_messages) == 1
    assert _last_note(agent) == "[system: the model powering this conversation is Test.]"


def test_activate_llm_profile_notes_model_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    project = tmp_path / "project"
    project.mkdir()
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        project_dir=project,
    )

    agent.activate_llm_profile(
        model="openai-responses:gpt-5",
        reasoning="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning=agent.subagent_reasoning,
        use_apply_patch=agent.use_apply_patch,
    )
    assert _last_note(agent) == "[system: the model powering this conversation changed from Test to GPT 5.]"

    agent.activate_llm_profile(
        model="test",
        reasoning="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning=agent.subagent_reasoning,
        use_apply_patch=agent.use_apply_patch,
    )
    assert _last_note(agent) == "[system: the model powering this conversation changed from GPT 5 to Test.]"

    # Effort- or subagent-only changes don't alter the main agent's context: no note.
    history_len = len(agent._context_messages)
    agent.activate_llm_profile(
        model="test",
        reasoning="high",
        subagent_model="openai-responses:gpt-5.4-mini",
        subagent_reasoning="high",
        use_apply_patch=agent.use_apply_patch,
    )
    assert len(agent._context_messages) == history_len


def test_model_change_note_without_file_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatSession(registry=DataConnectorRegistry(), model="test", reasoning="medium")

    agent.activate_llm_profile(
        model="openai-responses:gpt-5",
        reasoning="medium",
        subagent_model=agent.subagent_model,
        subagent_reasoning=agent.subagent_reasoning,
        use_apply_patch=agent.use_apply_patch,
    )
    assert _last_note(agent) == "[system: the model powering this conversation changed from Test to GPT 5.]"


def test_resolve_subagent_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-sub123456789cd9y")
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        subagent_model="openai-responses:gpt-5.4-mini",
    )
    assert agent.resolve_api_keys() == (None, "sk-sub123456789cd9y")


def test_thinking_settings_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatSession(registry=DataConnectorRegistry(), model="openai-responses:gpt-5", reasoning="high")
    # Unified level plus OpenAI's reasoning summary; no max_tokens override for non-Anthropic models.
    assert agent._thinking_settings() == {
        "thinking": "high",
        "openai_reasoning_summary": "detailed",
        "timeout": MAIN_REQUEST_TIMEOUT,
    }


def test_service_tier_is_omitted_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="openai-responses:gpt-5",
        reasoning="medium",
        subagent_model="openai-responses:gpt-5.4-mini",
    )
    assert agent._pydantic_ai_agent is not None
    assert agent._pydantic_ai_agent.model_settings == {}
    assert "service_tier" not in agent._subagent_model_settings()


def test_service_tier_applies_to_main_and_subagent_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="openai-responses:gpt-5",
        reasoning="medium",
        service_tier="priority",
        subagent_model="openai-responses:gpt-5.4-mini",
    )

    assert agent._pydantic_ai_agent is not None
    assert agent._pydantic_ai_agent.model_settings == {"service_tier": "priority"}
    assert agent._subagent_model_settings()["service_tier"] == "priority"


def test_false_explicitly_disables_main_and_subagent_reasoning() -> None:
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning=False,
        subagent_model="test",
        subagent_reasoning=False,
    )

    assert agent._thinking_settings()["thinking"] is False
    assert agent._subagent_model_settings()["thinking"] is False


def test_thinking_settings_budget_era_claude_raises_max_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    agent = ChatSession(
        registry=DataConnectorRegistry(), model="anthropic:claude-sonnet-4-5-20250929", reasoning="high"
    )
    settings = agent._thinking_settings()
    assert settings["thinking"] == "high"
    # sonnet-4-5 translates levels to budget_tokens (16384 for high); the API
    # requires max_tokens above the budget, and pydantic-ai's default is 4096.
    assert settings["max_tokens"] > 16384


def test_thinking_settings_adaptive_claude_no_max_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    agent = ChatSession(registry=DataConnectorRegistry(), model="anthropic:claude-opus-4-8", reasoning="high")
    # Adaptive-thinking models never use budgets — no max_tokens override.
    assert agent._thinking_settings() == {"thinking": "high", "timeout": MAIN_REQUEST_TIMEOUT}


def test_thinking_settings_opus_5_uses_upstream_adaptive_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    agent = ChatSession(registry=DataConnectorRegistry(), model="anthropic:claude-opus-5", reasoning="high")
    assert agent._thinking_settings() == {"thinking": "high", "timeout": MAIN_REQUEST_TIMEOUT}


def test_subagent_settings_budget_era_claude_raise_max_tokens() -> None:
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="low",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
        subagent_reasoning="high",
    )
    assert agent._subagent_model_settings() == {
        "thinking": "high",
        "max_tokens": 24576,
        "timeout": SUBAGENT_REQUEST_TIMEOUT,
    }


async def test_subagent_profile_wires_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    workspace = await _create_workspace_connector(tmp_path / "workspace.duckdb")
    try:
        agent = ChatSession(
            registry=DataConnectorRegistry(),
            model="test",
            reasoning="medium",
            workspace=workspace,
            subagent_model="anthropic:claude-opus-4-8",
            subagent_reasoning="low",
        )
        assert agent._tools.run_subagent_for_each_row is not None
        assert agent._tools.extract_rows_from_documents is not None
        assert agent._tools.run_subagent_for_each_row.subagent_llm == "anthropic:claude-opus-4-8"
        assert agent._tools.extract_rows_from_documents.subagent_llm == "anthropic:claude-opus-4-8"
        assert agent._tools.add_canonical_name.subagent_llm == "anthropic:claude-opus-4-8"
        assert agent._tools.get_data_source_document.summarizer_llm == "anthropic:claude-opus-4-8"
        subagent_settings = {"thinking": "low", "timeout": SUBAGENT_REQUEST_TIMEOUT}
        assert agent._tools.run_subagent_for_each_row.model_settings == subagent_settings
        assert agent._tools.get_data_source_document.model_settings == subagent_settings

        agent._tools.get_data_source_document._document_cache["cached"] = cast(Any, (workspace, "old summary"))
        agent.activate_llm_profile(
            model=agent.model,
            reasoning=agent.reasoning,
            subagent_model="openai-responses:gpt-5.4-mini",
            subagent_reasoning="high",
            use_apply_patch=agent.use_apply_patch,
        )
        assert agent._tools.get_data_source_document._document_cache == {}
        assert agent._tools.run_subagent_for_each_row.subagent_llm == "openai-responses:gpt-5.4-mini"
        assert agent._tools.extract_rows_from_documents.subagent_llm == "openai-responses:gpt-5.4-mini"
        assert agent._tools.add_canonical_name.subagent_llm == "openai-responses:gpt-5.4-mini"
        assert agent._tools.get_data_source_document.summarizer_llm == "openai-responses:gpt-5.4-mini"
        settings = cast(dict[str, Any], agent._tools.run_subagent_for_each_row.model_settings)
        assert settings is not None
        assert settings["thinking"] == "high"
        assert settings["openai_reasoning_summary"] == "detailed"
        assert "service_tier" not in settings
        settings = cast(dict[str, Any], agent._tools.extract_rows_from_documents.model_settings)
        assert settings["thinking"] == "high"
        assert settings["openai_reasoning_summary"] == "detailed"
        assert "service_tier" not in settings
        settings = cast(dict[str, Any], agent._tools.add_canonical_name.model_settings)
        assert settings["thinking"] == "high"
        assert settings["openai_reasoning_summary"] == "detailed"
        assert "service_tier" not in settings
        settings = cast(dict[str, Any], agent._tools.get_data_source_document.model_settings)
        assert settings["thinking"] == "high"
        assert settings["openai_reasoning_summary"] == "detailed"
        assert "service_tier" not in settings
    finally:
        await workspace.close_async()
