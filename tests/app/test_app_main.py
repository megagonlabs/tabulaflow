from __future__ import annotations

import sys

import pytest
import typer

from tabulaflow.app.config import LLM_OFF, AppConfig, LLMRoleConfig, LLMPreset, ResolvedLLMSelection
from tabulaflow.app.main import _resolve_startup_llm_selection
from tabulaflow.app.tui import app as tui


def _test_config() -> AppConfig:
    preset = LLMPreset(
        label="Test",
        main=LLMRoleConfig(model="test", reasoning_effort="medium"),
        subagent=LLMRoleConfig(model="test", reasoning_effort="low"),
    )
    return AppConfig(llm_preset=preset.label, custom_llm_presets=[preset])


def test_resolve_startup_llm_selection_uses_saved_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    resolved = _resolve_startup_llm_selection(llm_preset=None)

    preset = resolved.preset
    assert resolved.selection == "Test"
    assert preset is not None
    assert preset.label == "Test"
    assert preset.main == LLMRoleConfig(model="test", reasoning_effort="medium")
    assert preset.subagent == LLMRoleConfig(model="test", reasoning_effort="low")


def test_resolve_startup_llm_selection_auto_turns_off_without_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(app_config, "load_app_config", lambda: AppConfig())

    resolved = _resolve_startup_llm_selection(llm_preset=None)

    assert resolved.selection is None
    assert resolved.preset is None


def test_resolve_startup_llm_selection_cli_preset_overrides_saved_preset(
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

    resolved = _resolve_startup_llm_selection(llm_preset="CLI")

    assert resolved.selection == "CLI"
    assert resolved.preset == cli_preset


def test_resolve_startup_llm_selection_rejects_unknown_cli_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    with pytest.raises(typer.BadParameter, match="Unknown LLM preset: Missing"):
        _resolve_startup_llm_selection(llm_preset="Missing")


def test_resolve_startup_llm_selection_cli_off_overrides_saved_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    resolved = _resolve_startup_llm_selection(llm_preset="OFF")

    assert resolved.selection == LLM_OFF
    assert resolved.preset is None


def test_resolve_startup_llm_selection_returns_unverified_saved_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", _test_config)

    resolved = _resolve_startup_llm_selection(llm_preset=None)

    assert resolved.preset == _test_config().preset_by_label("Test")


class _FakeStdout:
    def __init__(self, *, tty: bool = True) -> None:
        self.tty = tty
        self.value = ""
        self.flushed = False

    def isatty(self) -> bool:
        return self.tty

    def write(self, value: str) -> int:
        self.value += value
        return len(value)

    def flush(self) -> None:
        self.flushed = True


class _FakeRunTuiApp:
    error: BaseException | None = None
    run_mouse: bool | None = None
    pane_close_args: list[bool] = []

    def __init__(self, **_kwargs: object) -> None:
        pass

    async def run_async(self, *, mouse: bool = True) -> None:
        type(self).run_mouse = mouse
        error = type(self).error
        if error is not None:
            raise error

    def _close_pane(self, *, remove_artifacts: bool = False) -> None:
        type(self).pane_close_args.append(remove_artifacts)


@pytest.mark.parametrize("error", [None, RuntimeError("boom")], ids=["normal", "error"])
async def test_run_tui_restores_terminal_modes(
    error: RuntimeError | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = _FakeStdout()
    _FakeRunTuiApp.error = error
    _FakeRunTuiApp.run_mouse = None
    _FakeRunTuiApp.pane_close_args = []

    monkeypatch.setattr(sys, "__stdout__", stdout)
    monkeypatch.setattr(tui, "TabulaflowApp", _FakeRunTuiApp)

    selection = ResolvedLLMSelection(LLM_OFF, None)
    if error is None:
        await tui.run_tui(selection)
    else:
        with pytest.raises(RuntimeError, match="boom"):
            await tui.run_tui(selection)

    assert _FakeRunTuiApp.run_mouse is True
    assert _FakeRunTuiApp.pane_close_args == [True]
    assert stdout.value == tui._TERMINAL_MODE_RESTORE_SEQUENCE
    assert stdout.flushed is True
