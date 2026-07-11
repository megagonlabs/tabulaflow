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
