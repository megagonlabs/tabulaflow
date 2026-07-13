from __future__ import annotations

from tabulaflow.app.session import compact_model_label, format_llm_error, format_llm_unavailable_message


def test_format_llm_error_normalizes_anthropic_api_key_message() -> None:
    raw = (
        "Set the `ANTHROPIC_API_KEY` environment variable or pass it via "
        "`AnthropicProvider(api_key=...)` to use the Anthropic provider."
    )

    assert format_llm_error(raw) == "Anthropic API key is not configured. Set ANTHROPIC_API_KEY."


def test_format_llm_error_normalizes_openai_api_key_message() -> None:
    assert format_llm_error("OPENAI_API_KEY environment variable not set") == (
        "OpenAI API key is not configured. Set OPENAI_API_KEY."
    )


def test_format_llm_error_normalizes_unknown_provider() -> None:
    assert format_llm_error("Unknown provider: nope") == "Unknown LLM provider in the selected preset."


def test_format_llm_error_has_generic_fallback() -> None:
    assert format_llm_error("provider exploded") == (
        "LLM provider is not configured correctly. Check the selected preset."
    )


def test_format_llm_unavailable_message_omits_raw_provider_detail() -> None:
    raw = (
        "Set the `ANTHROPIC_API_KEY` environment variable or pass it via "
        "`AnthropicProvider(api_key=...)` to use the Anthropic provider."
    )
    message = format_llm_unavailable_message(raw)

    assert message == "Select a configured preset in /config. /connect and data browsing still work."
    assert "Anthropic" not in message
    assert "ANTHROPIC_API_KEY" not in message
    assert "AnthropicProvider" not in message


def test_compact_model_label_matches_config_panel_labels() -> None:
    assert compact_model_label("anthropic:claude-opus-4-8", "high") == "Opus 4.8 high"
    assert compact_model_label("anthropic:claude-sonnet-4-5-20250929", "medium") == "Sonnet 4.5 medium"
    assert compact_model_label("openai-responses:gpt-5.4-mini", "medium") == "GPT 5.4 Mini medium"
