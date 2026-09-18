from __future__ import annotations

from tabulaflow.app.tui.app import LLM_UNAVAILABLE_MESSAGE
from tabulaflow.agents.llm import model_label


def test_llm_unavailable_message_is_provider_neutral() -> None:
    assert LLM_UNAVAILABLE_MESSAGE == ("Configure models in /config. /connect and browsing remain available.")
    assert "Anthropic" not in LLM_UNAVAILABLE_MESSAGE
    assert "ANTHROPIC_API_KEY" not in LLM_UNAVAILABLE_MESSAGE
    assert "AnthropicProvider" not in LLM_UNAVAILABLE_MESSAGE


def test_model_label_removes_only_provider_and_release_date() -> None:
    assert model_label("openai-responses:gpt-5.6-sol") == "gpt-5.6-sol"
    assert model_label("openai-responses:gpt-5-2025-08-07") == "gpt-5"
    assert model_label("anthropic:claude-sonnet-4-5-20250929") == "claude-sonnet-4-5"
    assert model_label("together:owner/model") == "owner/model"
    assert model_label("test") == "test"
