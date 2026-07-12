from __future__ import annotations

from tabulaflow.core.llm import reasoning_model_settings
from tabulaflow.research.agenthub.ensemblers.dbt_llm_ensembler import DbtLLMEnsemblerConfig
from tabulaflow.research.agenthub.ensemblers.llm_ensembler import LLMEnsemblerConfig
from tabulaflow.research.agenthub.utils import BasicAgentConfig


def test_reasoning_model_settings_maps_legacy_none_to_false() -> None:
    assert reasoning_model_settings("none") == {"thinking": False}
    assert reasoning_model_settings("high") == {"thinking": "high"}
    assert reasoning_model_settings(None) == {}


def test_basic_agent_config_uses_cross_provider_thinking() -> None:
    settings = BasicAgentConfig(reasoning_effort="high").to_model_settings()
    assert settings["thinking"] == "high"


def test_basic_agent_config_maps_none_to_false() -> None:
    settings = BasicAgentConfig(reasoning_effort="none").to_model_settings()
    assert settings["thinking"] is False


def test_ensembler_configs_use_cross_provider_thinking() -> None:
    llm_settings = LLMEnsemblerConfig(result_dirs=["a"], reasoning_effort="medium").to_model_settings()
    dbt_settings = DbtLLMEnsemblerConfig(result_dirs=["a"], reasoning_effort="low").to_model_settings()

    assert llm_settings["thinking"] == "medium"
    assert dbt_settings["thinking"] == "low"
