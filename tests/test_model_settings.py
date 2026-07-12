from __future__ import annotations

from tabulaflow.core.llm import make_model_settings
from tabulaflow.research.agenthub.ensemblers.dbt_llm_ensembler import DbtLLMEnsemblerConfig
from tabulaflow.research.agenthub.ensemblers.llm_ensembler import LLMEnsemblerConfig
from tabulaflow.research.agenthub.utils import BasicAgentConfig


def test_make_model_settings_maps_legacy_none_to_false() -> None:
    assert make_model_settings(model="anthropic:claude-sonnet-4-5-20250929", reasoning_effort="none") == {
        "thinking": False
    }
    assert make_model_settings(model="anthropic:claude-sonnet-4-5-20250929", reasoning_effort="high") == {
        "thinking": "high"
    }
    assert make_model_settings(model="openai-responses:gpt-5") == {}


def test_make_model_settings_adds_openai_summary_when_thinking() -> None:
    assert make_model_settings(model="openai-responses:gpt-5", reasoning_effort="high") == {
        "thinking": "high",
        "openai_reasoning_summary": "detailed",
    }


def test_make_model_settings_skips_summary_when_thinking_disabled() -> None:
    assert make_model_settings(model="openai-responses:gpt-5", reasoning_effort="none") == {"thinking": False}


def test_make_model_settings_skips_summary_for_other_providers() -> None:
    assert make_model_settings(model="anthropic:claude-sonnet-4-5-20250929", reasoning_effort="high") == {
        "thinking": "high"
    }


def test_make_model_settings_translates_service_tier_for_openai() -> None:
    assert make_model_settings(model="openai-responses:gpt-5", service_tier="priority") == {
        "openai_service_tier": "priority"
    }


def test_make_model_settings_skips_service_tier_for_other_providers() -> None:
    assert make_model_settings(model="anthropic:claude-sonnet-4-5-20250929", service_tier="priority") == {}


def test_make_model_settings_combines_reasoning_and_service_tier() -> None:
    assert make_model_settings(
        model="openai-responses:gpt-5",
        reasoning_effort="high",
        service_tier="priority",
    ) == {
        "thinking": "high",
        "openai_reasoning_summary": "detailed",
        "openai_service_tier": "priority",
    }


def test_basic_agent_config_uses_cross_provider_thinking() -> None:
    settings = BasicAgentConfig(reasoning_effort="high").to_model_settings()
    assert settings["thinking"] == "high"
    assert settings["openai_reasoning_summary"] == "detailed"


def test_basic_agent_config_maps_none_to_false() -> None:
    settings = BasicAgentConfig(reasoning_effort="none").to_model_settings()
    assert settings["thinking"] is False
    assert "openai_reasoning_summary" not in settings


def test_ensembler_configs_use_cross_provider_thinking() -> None:
    llm_settings = LLMEnsemblerConfig(result_dirs=["a"], reasoning_effort="medium").to_model_settings()
    dbt_settings = DbtLLMEnsemblerConfig(result_dirs=["a"], reasoning_effort="low").to_model_settings()

    assert llm_settings["thinking"] == "medium"
    assert llm_settings["openai_reasoning_summary"] == "detailed"
    assert dbt_settings["thinking"] == "low"
    assert dbt_settings["openai_reasoning_summary"] == "detailed"


def test_configs_use_provider_neutral_service_tier() -> None:
    basic_settings = BasicAgentConfig(service_tier="priority").to_model_settings()
    llm_settings = LLMEnsemblerConfig(result_dirs=["a"], service_tier="flex").to_model_settings()
    dbt_settings = DbtLLMEnsemblerConfig(result_dirs=["a"], service_tier="default").to_model_settings()

    assert basic_settings["openai_service_tier"] == "priority"
    assert llm_settings["openai_service_tier"] == "flex"
    assert dbt_settings["openai_service_tier"] == "default"
