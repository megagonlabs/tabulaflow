from __future__ import annotations

import json
from pathlib import Path

import pytest

from tabulaflow.app.config import (
    DEFAULT_MODEL_OPTIONS,
    DEFAULT_SUBAGENT_MODEL_OPTIONS,
    AppConfig,
    ModelOption,
    load_app_config,
    save_app_config,
    update_app_config,
)


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    config = load_app_config(str(tmp_path / "app_config.json"))
    assert config == AppConfig()
    assert list(config.model_options) == list(DEFAULT_MODEL_OPTIONS)
    assert list(config.subagent_model_options) == list(DEFAULT_SUBAGENT_MODEL_OPTIONS)


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    config = AppConfig(
        model="anthropic:claude-opus-4-8",
        reasoning_effort="high",
        subagent_model="openai-responses:gpt-5.4-mini",
        subagent_reasoning_effort="low",
    )
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
    path.write_text(json.dumps({"reasoning_effort": "minimal"}))
    with pytest.raises(ValueError, match=str(path)):
        load_app_config(str(path))


def test_load_invalid_subagent_effort_raises(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(json.dumps({"subagent_reasoning_effort": "minimal"}))
    with pytest.raises(ValueError, match=str(path)):
        load_app_config(str(path))


def test_assignment_validates() -> None:
    config = AppConfig()
    with pytest.raises(ValueError):
        config.reasoning_effort = "ultra"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        config.subagent_reasoning_effort = "ultra"  # type: ignore[assignment]


def test_defaults_not_written_to_file(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    config = AppConfig()
    config.model = "openai-responses:gpt-5.4-mini"
    save_app_config(config, str(path))
    # Only the deliberately-set field lands in the file — the catalog (and any
    # other default) stays live in code.
    assert json.loads(path.read_text()) == {"model": "openai-responses:gpt-5.4-mini"}


def test_custom_model_options_appended_to_defaults(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = ModelOption(model="together:my/model", label="Mine", recommended_effort="low")
    save_app_config(AppConfig(custom_model_options=[custom]), path)
    catalog = load_app_config(path).model_options
    # Defaults stay live from code; the custom entry rides along at the end.
    assert catalog == [*DEFAULT_MODEL_OPTIONS, custom]


def test_custom_subagent_model_options_appended_to_defaults(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = ModelOption(model="together:my/fast-model", label="Fast", recommended_effort="low")
    save_app_config(AppConfig(custom_subagent_model_options=[custom]), path)
    catalog = load_app_config(path).subagent_model_options
    assert catalog == [*DEFAULT_SUBAGENT_MODEL_OPTIONS, custom]


def test_custom_entry_overrides_matching_default_in_place(tmp_path: Path) -> None:
    override = ModelOption(model=DEFAULT_MODEL_OPTIONS[0].model, label="My GPT", recommended_effort="high")
    catalog = AppConfig(custom_model_options=[override]).model_options
    assert catalog[0] == override
    assert len(catalog) == len(DEFAULT_MODEL_OPTIONS)


def test_custom_subagent_entry_overrides_matching_default_in_place(tmp_path: Path) -> None:
    override = ModelOption(model=DEFAULT_SUBAGENT_MODEL_OPTIONS[0].model, label="My Worker", recommended_effort="low")
    catalog = AppConfig(custom_subagent_model_options=[override]).subagent_model_options
    assert catalog[0] == override
    assert len(catalog) == len(DEFAULT_SUBAGENT_MODEL_OPTIONS)


def test_update_preserves_custom_options(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    custom = [ModelOption(model="together:my/model", label="Mine")]
    subagent_custom = [ModelOption(model="together:my/fast-model", label="Fast")]
    save_app_config(AppConfig(custom_model_options=custom, custom_subagent_model_options=subagent_custom), path)
    update_app_config(
        path,
        model="together:my/model",
        reasoning_effort="low",
        subagent_model="anthropic:claude-opus-4-8",
        subagent_reasoning_effort="high",
    )
    config = load_app_config(path)
    assert config.model == "together:my/model"
    assert config.reasoning_effort == "low"
    assert config.subagent_model == "anthropic:claude-opus-4-8"
    assert config.subagent_reasoning_effort == "high"
    assert config.custom_model_options == custom
    assert config.custom_subagent_model_options == subagent_custom
