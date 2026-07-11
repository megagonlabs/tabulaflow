from __future__ import annotations

import pytest

from tabulaflow.chat import ChatAgent
from tabulaflow.core.db_connector.db_registry import DBRegistry


def test_set_model_failure_is_transactional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = ChatAgent(registry=DBRegistry(), model="test", reasoning_effort="medium")
    runtime_agent = agent._pydantic_ai_agent
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        agent.set_model("anthropic:claude-sonnet-4-5-20250929")
    # The failed switch left everything intact.
    assert agent.model == "test"
    assert agent._pydantic_ai_agent is runtime_agent


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


def test_thinking_settings_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    agent = ChatAgent(registry=DBRegistry(), model="openai-responses:gpt-5", reasoning_effort="high")
    # Unified level only — no max_tokens override for non-Anthropic models.
    assert agent._thinking_settings() == {"thinking": "high"}


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
