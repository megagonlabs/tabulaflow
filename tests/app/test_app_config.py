from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_ai.models import known_model_names

from tabulaflow.app.config import (
    ANTHROPIC_DEFAULT_LLM_CONFIG,
    CURATED_MODEL_CATALOG,
    LLM_OFF,
    OPENAI_DEFAULT_LLM_CONFIG,
    AppConfig,
    InvalidAppConfigError,
    LLMConfig,
    LLMRoleConfig,
    RECOMMENDED_MAIN_MODELS,
    ResolvedLLMConfig,
    llm_model_catalog,
    load_app_config,
    model_supports_apply_patch,
    resolve_llm_config,
    save_app_config,
    update_app_config,
)


def _config() -> LLMConfig:
    return LLMConfig(
        main=LLMRoleConfig(model="together:owner/main", effort="high"),
        subagent=LLMRoleConfig(model="together:owner/fast", effort="low"),
    )


def test_default_config_is_automatic() -> None:
    assert AppConfig().llm is None


def test_model_catalog_contains_recommendations_current_and_curated_models() -> None:
    catalog = llm_model_catalog(current="vendor:new-model", recommended=RECOMMENDED_MAIN_MODELS)
    assert catalog[:3] == (*RECOMMENDED_MAIN_MODELS, "vendor:new-model")
    assert "anthropic:claude-opus-5" in catalog
    assert "test" not in catalog
    assert not any(model.startswith("openai-chat:") for model in catalog)
    assert len(catalog) == len(set(catalog))
    assert set(CURATED_MODEL_CATALOG) <= set(known_model_names())


def test_model_catalog_keeps_a_current_openai_chat_model() -> None:
    current = "openai-chat:gpt-5-mini"

    catalog = llm_model_catalog(current=current, recommended=RECOMMENDED_MAIN_MODELS)

    assert catalog[:3] == (*RECOMMENDED_MAIN_MODELS, current)
    assert sum(model.startswith("openai-chat:") for model in catalog) == 1


def test_model_catalog_prioritizes_current_provider() -> None:
    catalog = llm_model_catalog(
        current="anthropic:claude-sonnet-5",
        recommended=("openai:gpt-5.6-sol",),
    )

    assert catalog[:4] == (
        "openai:gpt-5.6-sol",
        "anthropic:claude-sonnet-5",
        "anthropic:claude-opus-5",
        "anthropic:claude-opus-4-8",
    )
    assert catalog.index("xai:grok-4.20") < catalog.index("moonshotai:kimi-k3")
    assert catalog.index("moonshotai:kimi-k3") < catalog.index("deepseek:deepseek-v4-pro")


def test_model_catalog_only_includes_current_gateway_model() -> None:
    current = "gateway/openai:gpt-5.6-sol"

    catalog = llm_model_catalog(current=current, recommended=())

    assert current in catalog
    assert sum(model.startswith("gateway/") for model in catalog) == 1


def test_curated_openai_models_only_include_selected_gpt_families() -> None:
    openai_models = tuple(model for model in CURATED_MODEL_CATALOG if model.startswith("openai:"))
    assert openai_models == (
        "openai:gpt-6-astra",
        "openai:gpt-5.6-sol",
        "openai:gpt-5.6-terra",
        "openai:gpt-5.6-luna",
        "openai:gpt-5.6-cyber",
        "openai:gpt-5.5",
        "openai:gpt-5.4-mini",
        "openai:gpt-5-mini",
    )


def test_model_identifier_must_be_provider_qualified() -> None:
    with pytest.raises(ValueError, match="provider:model"):
        LLMRoleConfig(model="gpt-5")
    assert LLMRoleConfig(model=" openai:gpt-5 ").model == "openai:gpt-5"


def test_explicit_config_round_trip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    config = AppConfig(llm=_config())
    save_app_config(config, path)
    assert load_app_config(path) == config
    saved = json.loads(Path(path).read_text())
    assert saved["llm"]["main"] == {"model": "together:owner/main", "effort": "high"}


def test_old_reasoning_field_is_rejected() -> None:
    with pytest.raises(ValueError, match="reasoning"):
        AppConfig.model_validate(
            {"llm": {"main": {"model": "test", "reasoning": "high"}, "subagent": {"model": "test"}}}
        )


def test_off_round_trip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    save_app_config(AppConfig(llm=LLM_OFF), path)
    assert load_app_config(path).llm == LLM_OFF


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    assert load_app_config(str(tmp_path / "missing.json")) == AppConfig()


def test_invalid_or_old_config_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(json.dumps({"llm_preset": "OpenAI balanced"}))
    with pytest.raises(InvalidAppConfigError, match="llm_preset"):
        load_app_config(str(path))


def test_invalid_config_gets_a_concise_validation_error(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(
        json.dumps(
            {
                "llm": {
                    "main": {"model": "openai:gpt-5", "reasoning": "high"},
                    "subagent": {"model": "openai:gpt-5-mini", "reasoning": "medium"},
                }
            }
        )
    )

    with pytest.raises(InvalidAppConfigError) as exc_info:
        load_app_config(str(path))

    assert str(exc_info.value) == (
        f"Invalid app configuration: {path}\n"
        "llm.main.reasoning: Extra inputs are not permitted. Fix or delete the file."
    )


def test_resolve_explicit_and_off() -> None:
    config = _config()
    assert resolve_llm_config(AppConfig(llm=config)) == ResolvedLLMConfig(config, config)
    assert resolve_llm_config(AppConfig(llm=LLM_OFF)) == ResolvedLLMConfig(LLM_OFF, None)


def test_resolve_automatic_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    assert resolve_llm_config(AppConfig()) == ResolvedLLMConfig(None, ANTHROPIC_DEFAULT_LLM_CONFIG, "ANTHROPIC_API_KEY")
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    assert resolve_llm_config(AppConfig()) == ResolvedLLMConfig(None, OPENAI_DEFAULT_LLM_CONFIG, "OPENAI_API_KEY")


def test_resolve_without_credentials_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert resolve_llm_config(AppConfig()) == ResolvedLLMConfig(None, None)


def test_update_app_config(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    update_app_config(path, llm=_config())
    assert load_app_config(path).llm == _config()


@pytest.mark.parametrize(
    ("model", "supported"),
    [
        ("openai:gpt-5.6-sol", True),
        ("openai-responses:gpt-5.6-sol", True),
        ("openai:gpt-5", True),
        ("anthropic:claude-opus-5", False),
    ],
)
def test_apply_patch_support(model: str, supported: bool) -> None:
    assert model_supports_apply_patch(model) is supported
