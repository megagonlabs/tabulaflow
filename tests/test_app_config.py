from __future__ import annotations

import json
from pathlib import Path

import pytest

from tabulaflow.app.config import (
    DEFAULT_LLM_PRESETS,
    LLM_OFF,
    AppConfig,
    LLMRoleConfig,
    LLMPreset,
    ResolvedLLMSelection,
    load_app_config,
    resolve_llm_selection,
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
    assert config.llm_preset is None
    openai_budget = next(preset for preset in DEFAULT_LLM_PRESETS if preset.label == "OpenAI budget")
    assert openai_budget.main.model == "openai-responses:gpt-5.4-mini"
    assert openai_budget.main.reasoning_effort == "medium"
    assert openai_budget.subagent.model == "openai-responses:gpt-5-mini"
    assert openai_budget.subagent.reasoning_effort == "medium"
    assert openai_budget.enable_apply_patch is True
    anthropic_balanced = next(preset for preset in DEFAULT_LLM_PRESETS if preset.label == "Anthropic balanced")
    assert anthropic_balanced.main.model == "anthropic:claude-opus-5"
    assert anthropic_balanced.main.reasoning_effort == "high"
    assert anthropic_balanced.subagent.model == "anthropic:claude-sonnet-4-5-20250929"
    assert anthropic_balanced.subagent.reasoning_effort == "medium"
    assert anthropic_balanced.enable_apply_patch is False
    planning_hybrid = next(preset for preset in DEFAULT_LLM_PRESETS if preset.label == "Planning hybrid")
    assert planning_hybrid.main.model == "anthropic:claude-opus-4-8"
    assert planning_hybrid.main.reasoning_effort == "high"
    assert planning_hybrid.subagent.model == "openai-responses:gpt-5.4-mini"
    assert planning_hybrid.subagent.reasoning_effort == "medium"


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = _custom_preset()
    config = AppConfig(llm_preset=custom.label, custom_llm_presets=[custom])
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


def test_load_unknown_preset_fails_fast(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(json.dumps({"llm_preset": "missing"}))
    with pytest.raises(ValueError, match="Unknown LLM preset: missing"):
        load_app_config(str(path))


def test_unknown_preset_assignment_fails_fast() -> None:
    config = AppConfig(llm_preset="Anthropic balanced")
    with pytest.raises(ValueError, match="Unknown LLM preset: missing"):
        config.llm_preset = "missing"


def test_named_preset_resolves_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config = AppConfig(llm_preset="Anthropic balanced")
    resolved = resolve_llm_selection(config)
    assert resolved.selection == "Anthropic balanced"
    assert resolved.preset == config.preset_by_label("Anthropic balanced")


def test_named_override_resolves_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config = AppConfig()
    resolved = resolve_llm_selection(config, override="Anthropic balanced")
    assert resolved.selection == "Anthropic balanced"
    assert resolved.preset == config.preset_by_label("Anthropic balanced")


def test_unconfigured_prefers_openai_when_both_keys_are_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")

    resolved = resolve_llm_selection(AppConfig())

    assert resolved.selection is None
    assert resolved.preset == AppConfig().preset_by_label("OpenAI balanced")
    assert resolved.detected_api_key_env == "OPENAI_API_KEY"


def test_unconfigured_uses_anthropic_when_it_is_the_only_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")

    resolved = resolve_llm_selection(AppConfig())

    assert resolved.selection is None
    assert resolved.preset == AppConfig().preset_by_label("Anthropic balanced")
    assert resolved.detected_api_key_env == "ANTHROPIC_API_KEY"


def test_unconfigured_turns_llm_off_without_supported_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert resolve_llm_selection(AppConfig()).preset is None


def test_explicit_off_ignores_available_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")

    resolved = resolve_llm_selection(AppConfig(llm_preset=LLM_OFF))

    assert resolved.selection == LLM_OFF
    assert resolved.preset is None


def test_off_selection_is_normalized() -> None:
    assert AppConfig(llm_preset=" Off ").llm_preset == LLM_OFF


def test_resolved_selection_rejects_impossible_states() -> None:
    preset = DEFAULT_LLM_PRESETS[0]

    with pytest.raises(ValueError, match="off cannot resolve"):
        ResolvedLLMSelection(LLM_OFF, preset)
    with pytest.raises(ValueError, match="named LLM selection"):
        ResolvedLLMSelection("OpenAI balanced", None)
    with pytest.raises(ValueError, match="Detected credentials"):
        ResolvedLLMSelection("OpenAI balanced", preset, "OPENAI_API_KEY")


def test_assignment_validates() -> None:
    role = LLMRoleConfig(model="test:model")
    with pytest.raises(ValueError):
        role.reasoning_effort = "ultra"  # type: ignore[assignment]


def test_defaults_not_written_to_file(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    config = AppConfig()
    config.llm_preset = "Anthropic balanced"
    save_app_config(config, str(path))
    assert json.loads(path.read_text()) == {"llm_preset": "Anthropic balanced"}


def test_custom_presets_appended_to_defaults(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = _custom_preset()
    save_app_config(AppConfig(custom_llm_presets=[custom]), path)
    assert load_app_config(path).llm_presets == [*DEFAULT_LLM_PRESETS, custom]


def test_custom_preset_overrides_matching_default_in_place() -> None:
    override = LLMPreset(
        label=DEFAULT_LLM_PRESETS[0].label,
        main=LLMRoleConfig(model="openai-responses:gpt-5.6-sol", reasoning_effort="high"),
        subagent=LLMRoleConfig(model="openai-responses:gpt-5.4-mini", reasoning_effort="low"),
    )
    catalog = AppConfig(custom_llm_presets=[override]).llm_presets
    assert catalog[0] == override
    assert len(catalog) == len(DEFAULT_LLM_PRESETS)


def test_update_preserves_custom_presets(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = _custom_preset()
    save_app_config(AppConfig(custom_llm_presets=[custom]), path)
    update_app_config(path, llm_preset="Anthropic balanced")
    config = load_app_config(path)
    assert config.llm_preset == "Anthropic balanced"
    assert config.custom_llm_presets == [custom]


def test_update_persists_llm_off(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    save_app_config(AppConfig(llm_preset="Anthropic balanced"), path)

    update_app_config(path, llm_preset=LLM_OFF)

    assert load_app_config(path).llm_preset == LLM_OFF
    assert json.loads(Path(path).read_text())["llm_preset"] == LLM_OFF


@pytest.mark.parametrize("label", ["Off", "off", "OFF", " Off "])
def test_llm_selection_labels_are_reserved(label: str) -> None:
    with pytest.raises(ValueError, match="reserved"):
        _custom_preset(label)


def test_auto_is_available_as_an_ordinary_custom_preset_label() -> None:
    assert _custom_preset("Auto").label == "Auto"


def test_legacy_active_llm_preset_field_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(json.dumps({"active_llm_preset": None}))

    with pytest.raises(ValueError, match="active_llm_preset"):
        load_app_config(str(path))
