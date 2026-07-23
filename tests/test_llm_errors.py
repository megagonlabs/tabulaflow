from __future__ import annotations

from tabulaflow.app.session import LLM_UNAVAILABLE_MESSAGE
from tabulaflow.core.llm import compact_model_label


def test_llm_unavailable_message_is_provider_neutral() -> None:
    assert LLM_UNAVAILABLE_MESSAGE == ("Select a preset in /config. /connect and browsing remain available.")
    assert "Anthropic" not in LLM_UNAVAILABLE_MESSAGE
    assert "ANTHROPIC_API_KEY" not in LLM_UNAVAILABLE_MESSAGE
    assert "AnthropicProvider" not in LLM_UNAVAILABLE_MESSAGE


def test_compact_model_label_matches_config_panel_labels() -> None:
    assert compact_model_label("anthropic:claude-opus-4-8", "high") == "Opus 4.8 high"
    assert compact_model_label("anthropic:claude-sonnet-4-5-20250929", "medium") == "Sonnet 4.5 medium"
    assert compact_model_label("openai-responses:gpt-5.4-mini", "medium") == "GPT 5.4 Mini medium"
