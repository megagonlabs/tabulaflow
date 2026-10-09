from __future__ import annotations

from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError

from tabulaflow.app.tui.app import LLM_UNAVAILABLE_MESSAGE, _format_agent_turn_failure
from tabulaflow.agents.llm import model_label, provider_label


def test_llm_unavailable_message_is_provider_neutral() -> None:
    assert LLM_UNAVAILABLE_MESSAGE == ("Configure models in /config. Data connections and browsing remain available.")
    assert "Anthropic" not in LLM_UNAVAILABLE_MESSAGE
    assert "ANTHROPIC_API_KEY" not in LLM_UNAVAILABLE_MESSAGE
    assert "AnthropicProvider" not in LLM_UNAVAILABLE_MESSAGE


def test_model_label_removes_provider_namespaces_and_release_date() -> None:
    assert model_label("openai:gpt-5.6-sol") == "gpt-5.6-sol"
    assert model_label("openai:gpt-5-2025-08-07") == "gpt-5"
    assert model_label("anthropic:claude-sonnet-4-5-20250929") == "claude-sonnet-4-5"
    assert model_label("fireworks:accounts/fireworks/models/kimi-k3") == "kimi-k3"
    assert model_label("together:owner/model") == "model"
    assert model_label("test") == "test"


def test_provider_label_uses_friendly_names_and_fallback() -> None:
    assert provider_label("openai:gpt-5") == "OpenAI"
    assert provider_label("google-cloud:gemini-2.5-pro") == "Google Vertex AI"
    assert provider_label("bedrock:anthropic.claude") == "AWS Bedrock"
    assert provider_label("custom-provider:model") == "Custom Provider"
    assert provider_label("test") == "Model provider"


def test_agent_turn_failure_shows_provider_and_http_status() -> None:
    error = ModelHTTPError(429, "gpt-5", {"error": "sensitive provider body"})

    assert _format_agent_turn_failure(error, model="openai:gpt-5") == (
        "OpenAI request failed (HTTP 429): Rate limit exceeded. Wait and retry."
    )


def test_agent_turn_failure_classifies_chained_connection_error() -> None:
    class APIConnectionError(Exception):
        pass

    error = ModelAPIError("claude-sonnet", "Connection error.")
    error.__cause__ = APIConnectionError("DNS lookup included internal details")

    assert _format_agent_turn_failure(error, model="anthropic:claude-sonnet") == (
        "Couldn’t connect to Anthropic. Check your network, proxy, and provider endpoint, then retry."
    )


def test_agent_turn_failure_classifies_chained_timeout() -> None:
    error = ModelAPIError("gemini", "Request failed.")
    error.__cause__ = TimeoutError("internal timeout detail")

    assert _format_agent_turn_failure(error, model="google-cloud:gemini") == (
        "Google Vertex AI request timed out after retries. Try again."
    )


def test_agent_turn_failure_preserves_non_model_error() -> None:
    assert _format_agent_turn_failure(RuntimeError("agent failure detail"), model="openai:gpt-5") == (
        "agent failure detail."
    )
