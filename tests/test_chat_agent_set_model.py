from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from tabulaflow.app.session import create_workspace_connector
from tabulaflow.chat import ChatAgent
from tabulaflow.core.db_connector.db_registry import DBRegistry


def test_set_llm_profile_failure_is_transactional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = ChatAgent(registry=DBRegistry(), model="test", reasoning_effort="medium")
    runtime_agent = agent._pydantic_ai_agent
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        agent.set_llm_profile(
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
        agent.set_llm_profile(
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


def test_set_llm_profile_preserves_conversation_state(monkeypatch: pytest.MonkeyPatch) -> None:
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

    agent.set_llm_profile(
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


def test_api_key_read_from_live_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(registry=DBRegistry(), model="openai-responses:gpt-5", reasoning_effort="medium")
    assert agent.api_key == "sk-test123456789ab4x"


def test_api_key_none_for_keyless_model() -> None:
    agent = ChatAgent(registry=DBRegistry(), model="test", reasoning_effort="medium")
    assert agent.api_key is None


def test_supported_efforts_from_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(registry=DBRegistry(), model="openai-responses:gpt-5", reasoning_effort="medium")
    assert agent.supported_efforts == ("low", "medium", "high", "xhigh")


def test_supported_efforts_empty_for_non_thinking_model() -> None:
    agent = ChatAgent(registry=DBRegistry(), model="test", reasoning_effort="medium")
    assert agent.supported_efforts == ()


def test_subagent_api_key_and_supported_efforts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-sub123456789cd9y")
    agent = ChatAgent(
        registry=DBRegistry(),
        model="test",
        reasoning_effort="medium",
        subagent_model="openai-responses:gpt-5.4-mini",
    )
    assert agent.subagent_api_key == "sk-sub123456789cd9y"
    assert agent.subagent_supported_efforts == ("low", "medium", "high", "xhigh")


def test_thinking_settings_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(registry=DBRegistry(), model="openai-responses:gpt-5", reasoning_effort="high")
    # Unified level plus OpenAI's reasoning summary; no max_tokens override for non-Anthropic models.
    assert agent._thinking_settings() == {
        "thinking": "high",
        "openai_reasoning_summary": "detailed",
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
    assert agent._thinking_settings() == {"thinking": "high"}


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
        assert agent._tools.run_subagent_for_each_row.model_settings == {"thinking": "low"}
        assert agent._tools.get_db_document.model_settings == {"thinking": "low"}

        agent._tools.get_db_document._document_cache["cached"] = cast(Any, (workspace, "old summary"))
        agent.set_llm_profile(
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
