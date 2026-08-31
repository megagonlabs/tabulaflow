from __future__ import annotations

import pytest

from tabulaflow.agents.llm import ReasoningEffort, make_model_settings
from tabulaflow.research.agents.ensemblers.dbt import DbtLLMEnsemblerConfig
from tabulaflow.research.agents.ensemblers.llm import LLMEnsemblerConfig
from tabulaflow.research.agents.utils import BasicAgentConfig


def test_make_model_settings_accepts_shared_reasoning_values() -> None:
    assert make_model_settings(model="anthropic:claude-sonnet-4-5-20250929", reasoning="high") == {
        "thinking": "high",
        "max_tokens": 24576,
    }
    assert make_model_settings(model="openai-responses:gpt-5") == {}


def test_make_model_settings_adds_openai_summary_when_thinking() -> None:
    assert make_model_settings(model="openai-responses:gpt-5", reasoning="high") == {
        "thinking": "high",
        "openai_reasoning_summary": "detailed",
    }


def test_make_model_settings_skips_summary_when_thinking_disabled() -> None:
    assert make_model_settings(model="openai-responses:gpt-5", reasoning=False) == {"thinking": False}


def test_make_model_settings_skips_summary_for_other_providers() -> None:
    assert make_model_settings(model="anthropic:claude-sonnet-4-5-20250929", reasoning="high") == {
        "thinking": "high",
        "max_tokens": 24576,
    }


@pytest.mark.parametrize(
    ("effort", "budget"),
    [("minimal", 1024), ("low", 2048), ("medium", 10000), ("high", 16384), ("xhigh", 32768)],
)
def test_budget_thinking_claude_reserves_answer_tokens(effort: ReasoningEffort, budget: int) -> None:
    settings = make_model_settings(
        model="anthropic:claude-sonnet-4-5-20250929",
        reasoning=effort,
    )
    assert settings == {"thinking": effort, "max_tokens": budget + 8192}


def test_budget_thinking_claude_on_vertex_reserves_answer_tokens() -> None:
    settings = make_model_settings(
        model="google-cloud:claude-sonnet-4-5@20250929",
        reasoning="medium",
    )
    assert settings == {"thinking": "medium", "max_tokens": 18192}


def test_adaptive_thinking_claude_does_not_set_max_tokens() -> None:
    settings = make_model_settings(model="anthropic:claude-opus-4-8", reasoning="high")
    assert settings == {"thinking": "high"}


def test_opus_5_uses_upstream_adaptive_profile() -> None:
    settings = make_model_settings(model="anthropic:claude-opus-5", reasoning="high")
    assert settings == {"thinking": "high"}


def test_make_model_settings_uses_cross_provider_service_tier() -> None:
    assert make_model_settings(model="openai-responses:gpt-5", service_tier="priority") == {"service_tier": "priority"}
    assert make_model_settings(model="anthropic:claude-sonnet-4-5-20250929", service_tier="priority") == {
        "service_tier": "priority"
    }


def test_make_model_settings_combines_reasoning_and_service_tier() -> None:
    assert make_model_settings(
        model="openai-responses:gpt-5",
        reasoning="high",
        service_tier="priority",
    ) == {
        "thinking": "high",
        "openai_reasoning_summary": "detailed",
        "service_tier": "priority",
    }


def test_basic_agent_config_uses_cross_provider_thinking() -> None:
    settings = BasicAgentConfig(reasoning="high").to_model_settings()
    assert settings["thinking"] == "high"
    assert settings["openai_reasoning_summary"] == "detailed"


def test_basic_agent_config_maps_false_to_disabled_thinking() -> None:
    settings = BasicAgentConfig(reasoning=False).to_model_settings()
    assert settings["thinking"] is False
    assert "openai_reasoning_summary" not in settings


def test_ensembler_configs_use_cross_provider_thinking() -> None:
    llm_settings = LLMEnsemblerConfig(result_dirs=["a"], reasoning="medium").to_model_settings()
    dbt_settings = DbtLLMEnsemblerConfig(result_dirs=["a"], reasoning="low").to_model_settings()

    assert llm_settings["thinking"] == "medium"
    assert llm_settings["openai_reasoning_summary"] == "detailed"
    assert dbt_settings["thinking"] == "low"
    assert dbt_settings["openai_reasoning_summary"] == "detailed"


def test_configs_use_provider_neutral_service_tier() -> None:
    basic_settings = BasicAgentConfig(service_tier="priority").to_model_settings()
    llm_settings = LLMEnsemblerConfig(result_dirs=["a"], service_tier="flex").to_model_settings()
    dbt_settings = DbtLLMEnsemblerConfig(result_dirs=["a"], service_tier="default").to_model_settings()

    assert basic_settings["service_tier"] == "priority"
    assert llm_settings["service_tier"] == "flex"
    assert dbt_settings["service_tier"] == "default"
