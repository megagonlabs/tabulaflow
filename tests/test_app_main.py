from __future__ import annotations

import pytest
import typer

from tabulaflow.app.config import AppConfig, LLMRoleConfig, LLMPreset
from tabulaflow.app.main import _resolve_llm_roles


def _test_config() -> AppConfig:
    preset = LLMPreset(
        label="Test",
        main=LLMRoleConfig(model="test", reasoning_effort="medium"),
        subagent=LLMRoleConfig(model="test", reasoning_effort="low"),
    )
    return AppConfig(active_llm_preset=preset.label, custom_llm_presets=[preset])


def test_resolve_llm_roles_uses_saved_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    main, subagent = _resolve_llm_roles(
        model=None,
        reasoning_effort=None,
        subagent_model=None,
        subagent_reasoning_effort=None,
    )

    assert main == LLMRoleConfig(model="test", reasoning_effort="medium")
    assert subagent == LLMRoleConfig(model="test", reasoning_effort="low")


def test_resolve_llm_roles_applies_cli_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    main, subagent = _resolve_llm_roles(
        model="test",
        reasoning_effort="high",
        subagent_model="test",
        subagent_reasoning_effort="medium",
    )

    assert main == LLMRoleConfig(model="test", reasoning_effort="high")
    assert subagent == LLMRoleConfig(model="test", reasoning_effort="medium")


def test_resolve_llm_roles_rejects_invalid_cli_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    with pytest.raises(typer.BadParameter, match="'ultra' is not one of"):
        _resolve_llm_roles(
            model=None,
            reasoning_effort="ultra",
            subagent_model=None,
            subagent_reasoning_effort=None,
        )


def test_resolve_llm_roles_rejects_invalid_cli_model(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    with pytest.raises(typer.BadParameter, match="'nope:model' is not a usable LLM model"):
        _resolve_llm_roles(
            model="nope:model",
            reasoning_effort=None,
            subagent_model=None,
            subagent_reasoning_effort=None,
        )


def test_resolve_llm_roles_rejects_invalid_saved_model(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    preset = LLMPreset(
        label="Broken",
        main=LLMRoleConfig(model="nope:model", reasoning_effort="medium"),
        subagent=LLMRoleConfig(model="test", reasoning_effort="medium"),
    )
    monkeypatch.setattr(
        app_config,
        "load_app_config",
        lambda: AppConfig(active_llm_preset=preset.label, custom_llm_presets=[preset]),
    )

    with pytest.raises(typer.BadParameter, match="'nope:model' is not a usable LLM model"):
        _resolve_llm_roles(
            model=None,
            reasoning_effort=None,
            subagent_model=None,
            subagent_reasoning_effort=None,
        )
