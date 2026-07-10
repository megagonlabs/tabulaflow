from __future__ import annotations

import json
from pathlib import Path

import pytest

from tabulaflow.app.config import AppConfig, load_app_config, save_app_config


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    config = load_app_config(str(tmp_path / "app_config.json"))
    assert config == AppConfig()


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    config = AppConfig(model="anthropic:claude-sonnet-4-5-20250929", reasoning_effort="high")
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
    path.write_text(json.dumps({"reasoning_effort": "ultra"}))
    with pytest.raises(ValueError, match=str(path)):
        load_app_config(str(path))


def test_assignment_validates() -> None:
    config = AppConfig()
    with pytest.raises(ValueError):
        config.reasoning_effort = "ultra"  # type: ignore[assignment]
