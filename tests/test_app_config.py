from __future__ import annotations

import json
from pathlib import Path

import pytest

from tabulaflow.app.config import (
    DEFAULT_LLM_PRESETS,
    AppConfig,
    LLMRoleConfig,
    LLMPreset,
    load_app_config,
    save_app_config,
    update_app_config,
)


def _custom_preset(label: str = "My stack") -> LLMPreset:
    return LLMPreset(
        label=label,
        main=LLMRoleConfig(model="together:my/model", reasoning_effort="low"),
        subagent=LLMRoleConfig(model="together:my/fast-model", reasoning_effort="medium"),
    )


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    config = load_app_config(str(tmp_path / "app_config.json"))
    assert config == AppConfig()
    assert config.llm_presets == list(DEFAULT_LLM_PRESETS)
    assert config.active_preset == DEFAULT_LLM_PRESETS[0]
    openai_budget = next(preset for preset in DEFAULT_LLM_PRESETS if preset.label == "OpenAI budget")
    assert openai_budget.main.model == "openai-responses:gpt-5.4-mini"
    assert openai_budget.main.reasoning_effort == "medium"
    assert openai_budget.subagent.model == "openai-responses:gpt-5-mini"
    assert openai_budget.subagent.reasoning_effort == "medium"
    planning_hybrid = next(preset for preset in DEFAULT_LLM_PRESETS if preset.label == "Planning hybrid")
    assert planning_hybrid.main.model == "anthropic:claude-opus-4-8"
    assert planning_hybrid.main.reasoning_effort == "high"
    assert planning_hybrid.subagent.model == "openai-responses:gpt-5.4-mini"
    assert planning_hybrid.subagent.reasoning_effort == "medium"


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = _custom_preset()
    config = AppConfig(active_llm_preset=custom.label, custom_llm_presets=[custom])
    save_app_config(config, path)
    assert load_app_config(path) == config


def test_save_creates_parent_dir(tmp_path: Path) -> None:
    path = str(tmp_path / "nested" / "app_config.json")
    save_app_config(AppConfig(), path)
    assert load_app_config(path) == AppConfig()


def test_load_malformed_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text("{not json")
    with pytest.raises(ValueError, match=str(path)):
        load_app_config(str(path))


def test_load_invalid_effort_raises(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(
        json.dumps(
            {
                "custom_llm_presets": [
                    {
                        "label": "Bad",
                        "main": {"model": "test:main", "reasoning_effort": "minimal"},
                        "subagent": {"model": "test:subagent", "reasoning_effort": "medium"},
                    }
                ]
            }
        )
    )
    with pytest.raises(ValueError, match=str(path)):
        load_app_config(str(path))


def test_load_unknown_active_preset_raises(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(json.dumps({"active_llm_preset": "missing"}))
    with pytest.raises(ValueError, match=str(path)):
        load_app_config(str(path))


def test_assignment_validates() -> None:
    role = LLMRoleConfig(model="test:model")
    with pytest.raises(ValueError):
        role.reasoning_effort = "ultra"  # type: ignore[assignment]


def test_defaults_not_written_to_file(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    config = AppConfig()
    config.active_llm_preset = "Anthropic balanced"
    save_app_config(config, str(path))
    assert json.loads(path.read_text()) == {"active_llm_preset": "Anthropic balanced"}


def test_custom_presets_appended_to_defaults(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = _custom_preset()
    save_app_config(AppConfig(custom_llm_presets=[custom]), path)
    assert load_app_config(path).llm_presets == [*DEFAULT_LLM_PRESETS, custom]


def test_custom_preset_overrides_matching_default_in_place() -> None:
    override = LLMPreset(
        label=DEFAULT_LLM_PRESETS[0].label,
        main=LLMRoleConfig(model="openai-responses:gpt-5.5", reasoning_effort="high"),
        subagent=LLMRoleConfig(model="openai-responses:gpt-5.4-mini", reasoning_effort="low"),
    )
    catalog = AppConfig(custom_llm_presets=[override]).llm_presets
    assert catalog[0] == override
    assert len(catalog) == len(DEFAULT_LLM_PRESETS)


def test_update_preserves_custom_presets(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = _custom_preset()
    save_app_config(AppConfig(custom_llm_presets=[custom]), path)
    update_app_config(path, active_llm_preset="Anthropic balanced")
    config = load_app_config(path)
    assert config.active_llm_preset == "Anthropic balanced"
    assert config.custom_llm_presets == [custom]
