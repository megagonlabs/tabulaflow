from __future__ import annotations

import json
from pathlib import Path

import pytest

from tabulaflow.app.config import (
    DEFAULT_MODEL_OPTIONS,
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


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    config = AppConfig(model="anthropic:claude-opus-4-8", reasoning_effort="high")
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


def test_assignment_validates() -> None:
    config = AppConfig()
    with pytest.raises(ValueError):
        config.reasoning_effort = "ultra"  # type: ignore[assignment]


def test_defaults_not_written_to_file(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    config = AppConfig()
    config.model = "openai-responses:gpt-5.4-mini"
    save_app_config(config, str(path))
    # Only the deliberately-set field lands in the file — the catalog (and any
    # other default) stays live in code.
    assert json.loads(path.read_text()) == {"model": "openai-responses:gpt-5.4-mini"}


def test_custom_model_options_roundtrip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    options = [ModelOption(model="together:my/model", label="Mine", recommended_effort="low")]
    save_app_config(AppConfig(model_options=options), path)
    assert load_app_config(path).model_options == options


def test_update_preserves_custom_options(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    options = [ModelOption(model="together:my/model", label="Mine")]
    save_app_config(AppConfig(model_options=options), path)
    update_app_config(path, model="together:my/model", reasoning_effort="low")
    config = load_app_config(path)
    assert config.model == "together:my/model"
    assert config.reasoning_effort == "low"
    assert config.model_options == options
