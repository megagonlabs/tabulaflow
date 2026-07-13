from __future__ import annotations

import pytest
import typer

from tabulaflow.app.config import AppConfig, LLMRoleConfig, LLMPreset
from tabulaflow.app.main import _resolve_startup_llm_preset


def _test_config() -> AppConfig:
    preset = LLMPreset(
        label="Test",
        main=LLMRoleConfig(model="test", reasoning_effort="medium"),
        subagent=LLMRoleConfig(model="test", reasoning_effort="low"),
    )
    return AppConfig(active_llm_preset=preset.label, custom_llm_presets=[preset])


def test_resolve_startup_llm_preset_uses_saved_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    preset = _resolve_startup_llm_preset(llm_preset=None)

    assert preset is not None
    assert preset.label == "Test"
    assert preset.main == LLMRoleConfig(model="test", reasoning_effort="medium")
    assert preset.subagent == LLMRoleConfig(model="test", reasoning_effort="low")


def test_resolve_startup_llm_preset_returns_none_without_active_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", lambda: AppConfig())

    preset = _resolve_startup_llm_preset(llm_preset=None)

    assert preset is None


def test_resolve_startup_llm_preset_cli_preset_overrides_saved_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tabulaflow.app.config as app_config

    cli_preset = LLMPreset(
        label="CLI",
        main=LLMRoleConfig(model="cli-main", reasoning_effort="high"),
        subagent=LLMRoleConfig(model="cli-subagent", reasoning_effort="medium"),
    )

    def config() -> AppConfig:
        saved = _test_config()
        saved.custom_llm_presets.append(cli_preset)
        return saved

    monkeypatch.setattr(app_config, "load_app_config", config)

    preset = _resolve_startup_llm_preset(llm_preset="CLI")

    assert preset == cli_preset


def test_resolve_startup_llm_preset_rejects_unknown_cli_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    with pytest.raises(typer.BadParameter, match="Unknown LLM preset: Missing"):
        _resolve_startup_llm_preset(llm_preset="Missing")


def test_resolve_startup_llm_preset_returns_none_for_missing_saved_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", lambda: AppConfig(active_llm_preset="Missing"))

    resolved = _resolve_startup_llm_preset(llm_preset=None)

    assert resolved is None


def test_resolve_startup_llm_preset_returns_unverified_saved_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    resolved = _resolve_startup_llm_preset(llm_preset=None)

    assert resolved == _test_config().active_preset
