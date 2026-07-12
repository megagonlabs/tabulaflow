from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from textual.app import App

from tabulaflow.app.config import LLMRoleConfig, LLMPreset
from tabulaflow.app.screens import ConfigScreen

_PRESETS = [
    LLMPreset(
        id="openai-balanced",
        label="OpenAI balanced",
        main=LLMRoleConfig(model="openai-responses:gpt-5.5", reasoning_effort="medium"),
        subagent=LLMRoleConfig(model="openai-responses:gpt-5.4-mini", reasoning_effort="medium"),
    ),
    LLMPreset(
        id="anthropic-balanced",
        label="Anthropic balanced",
        main=LLMRoleConfig(model="anthropic:claude-opus-4-8", reasoning_effort="high"),
        subagent=LLMRoleConfig(model="anthropic:claude-sonnet-4-5-20250929", reasoning_effort="high"),
    ),
]


class _StubSession:
    def __init__(
        self,
        model: str = "openai-responses:gpt-5.5",
        reasoning_effort: str = "medium",
        subagent_model: str = "openai-responses:gpt-5.4-mini",
        subagent_reasoning_effort: str = "medium",
    ) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.subagent_model = subagent_model
        self.subagent_reasoning_effort = subagent_reasoning_effort
        self.api_key: str | None = None
        self.subagent_api_key: str | None = None

    def set_main_profile(self, *, model: str, reasoning_effort: str) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort

    def set_subagent_profile(self, *, model: str, reasoning_effort: str) -> None:
        self.subagent_model = model
        self.subagent_reasoning_effort = reasoning_effort


class _App(App[None]):
    def __init__(self, screen: ConfigScreen) -> None:
        super().__init__()
        self._config_screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._config_screen)


@pytest.fixture(autouse=True)
def _patch_config_io(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    monkeypatch.setattr(
        "tabulaflow.app.screens.load_app_config",
        lambda: SimpleNamespace(llm_presets=list(_PRESETS)),
    )
    updates: list[dict[str, Any]] = []
    monkeypatch.setattr("tabulaflow.app.screens.update_app_config", lambda **prefs: updates.append(prefs))
    return updates


@pytest.fixture
def updates(_patch_config_io: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _patch_config_io


async def test_renders_presets() -> None:
    session = _StubSession()
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert len(screen._preset_rows) == 2
        assert screen._cursor == 0
        assert "●" in screen._render_preset_row(0).plain
        assert "OpenAI balanced" in screen._render_preset_row(0).plain
        assert "GPT 5.5 medium" in screen._render_preset_row(0).plain
        assert "GPT 5.4 Mini medium" in screen._render_preset_row(0).plain
        assert "Opus 4.8 high" in screen._render_preset_row(1).plain
        assert "Sonnet 4.5 high" in screen._render_preset_row(1).plain
        assert "Claude" not in screen._render_preset_row(1).plain
        assert "20250929" not in screen._render_preset_row(1).plain
        assert "●" not in screen._render_preset_row(1).plain


async def test_enter_selects_preset_and_persists(updates: list[dict[str, Any]]) -> None:
    session = _StubSession()
    refreshed: list[bool] = []
    screen = ConfigScreen(session, on_change=lambda: refreshed.append(True))  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "enter")
        assert session.model == "anthropic:claude-opus-4-8"
        assert session.reasoning_effort == "high"
        assert session.subagent_model == "anthropic:claude-sonnet-4-5-20250929"
        assert session.subagent_reasoning_effort == "high"
        assert updates == [{"active_llm_preset": "anthropic-balanced"}]
        assert refreshed
        assert "●" in screen._render_preset_row(1).plain


async def test_active_preset_shows_api_keys() -> None:
    session = _StubSession()
    session.api_key = "sk-main123456789E0QA"
    session.subagent_api_key = session.api_key
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert " · API key ***E0QA" in screen._render_preset_row(0).plain
        assert "\n      API key" not in screen._render_preset_row(0).plain
        assert screen._render_preset_row(0).plain.count("API key ***E0QA") == 1
        assert "API key" not in screen._render_preset_row(1).plain


async def test_active_mixed_preset_shows_distinct_api_keys() -> None:
    session = _StubSession(
        model="openai-responses:gpt-5.5",
        reasoning_effort="high",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
        subagent_reasoning_effort="medium",
    )
    session.api_key = "sk-main1234567890000"
    session.subagent_api_key = "sk-sub1234567891111"
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert " · API key ***0000 · API key ***1111" in screen._render_preset_row(0).plain
        await pilot.press("down")
        assert "API key" in screen._render_preset_row(0).plain
        assert "API key" not in screen._render_preset_row(1).plain


async def test_active_preset_wraps_api_keys_with_indent() -> None:
    session = _StubSession()
    session.api_key = "sk-main123456789E0QA"
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert "\n      API key ***E0QA" in screen._render_preset_row(0, available_width=48).plain


async def test_short_api_key_omitted() -> None:
    session = _StubSession()
    session.api_key = "short"
    session.subagent_api_key = "sk-sub1234567891111"
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert "short" not in screen._render_preset_row(0).plain
        assert "API key ***1111" in screen._render_preset_row(0).plain


async def test_current_custom_row_for_unmatched_runtime_profile(updates: list[dict[str, Any]]) -> None:
    session = _StubSession(
        model="openai-responses:gpt-5.5",
        reasoning_effort="high",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
        subagent_reasoning_effort="medium",
    )
    refreshed: list[bool] = []
    screen = ConfigScreen(session, on_change=lambda: refreshed.append(True))  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert len(screen._preset_rows) == 3
        assert screen._cursor == 0
        assert "● Current custom" in screen._render_preset_row(0).plain
        await pilot.press("enter")
        assert updates == []
        assert refreshed
        await pilot.press("down", "enter")
        assert updates == [{"active_llm_preset": "openai-balanced"}]
        assert session.reasoning_effort == "medium"


async def test_select_failure_shows_inline_error(updates: list[dict[str, Any]]) -> None:
    class _FailingSession(_StubSession):
        def set_main_profile(self, *, model: str, reasoning_effort: str) -> None:
            if model.startswith("anthropic:"):
                raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
            super().set_main_profile(model=model, reasoning_effort=reasoning_effort)

    session = _FailingSession()
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "enter")
        assert session.model == "openai-responses:gpt-5.5"
        assert updates == []
        assert "ANTHROPIC_API_KEY" in screen._render_preset_row(1).plain
        assert "●" in screen._render_preset_row(0).plain
        await pilot.press("up", "enter")
        assert "ANTHROPIC_API_KEY" not in screen._render_preset_row(1).plain
