from __future__ import annotations

from textual.app import App
from textual.widgets import Static

from tabulaflow.app.config import LLMConfig, LLMRoleConfig, ResolvedLLMConfig
from tabulaflow.app.tui.screens.config import ConfigScreen, ModelPickerScreen


_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="openai-responses:gpt-5.6-sol", reasoning="medium"),
    subagent=LLMRoleConfig(model="openai-responses:gpt-5.4-mini", reasoning="low"),
)


class _App(App[None]):
    def __init__(self, screen: ConfigScreen) -> None:
        super().__init__()
        self.screen_to_open = screen
        self.results: list[ResolvedLLMConfig | None] = []

    def on_mount(self) -> None:
        self.push_screen(self.screen_to_open, self.results.append)


def _text(screen: ConfigScreen, selector: str) -> str:
    return str(screen.query_one(selector, Static).render())


async def test_config_screen_shows_role_fields_and_exact_identifiers() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert "enabled" in _text(screen, "#field-enabled")
        assert "openai-responses:gpt-5.6-sol" in _text(screen, "#field-main-model")
        assert "openai-responses:gpt-5.4-mini" in _text(screen, "#field-subagent-model")
        assert "medium" in _text(screen, "#field-main-reasoning")
        assert "Subagent model" in _text(screen, "#field-subagent-model")
        assert "Subagent reasoning" in _text(screen, "#field-subagent-reasoning")
        assert not list(screen.query("#config-credentials"))
        rendered = {str(widget.render()) for widget in screen.query(Static)}
        assert "MAIN AGENT" not in rendered
        assert "SUBAGENT" not in rendered


async def test_fields_are_edited_and_applied_atomically() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert "(recommended)" in str(picker.query_one("#model-options", Static).render())
        assert not list(picker.query("#model-search"))
        await pilot.press("down", "enter")
        await pilot.pause()
        assert screen.dirty
        await pilot.press("escape")
        await pilot.pause()
        result = app.results[0]
        assert result is not None and result.config is not None
        assert result.config.main.model == "openai-responses:gpt-5.4-mini"
        assert result.config.subagent == _CONFIG.subagent


async def test_disable_and_apply() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("enter", "escape")
        await pilot.pause()
        assert app.results == [ResolvedLLMConfig("off", None)]


async def test_escape_discards_clean_screen() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()
        assert app.results == [None]


async def test_reasoning_changes_inline_with_left_and_right() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "down", "right")
        await pilot.pause()
        assert "high" in _text(screen, "#field-main-reasoning")
        assert app.screen is screen
        await pilot.press("left", "escape")
        await pilot.pause()
        assert app.results == [None]


async def test_model_picker_filters_without_search_input() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter", "a", "n", "t", "h")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert "“anth”" in str(picker.query_one("#model-picker-title", Static).render())
        options = str(picker.query_one("#model-options", Static).render())
        assert "anthropic:" in options
        assert "openai-responses:" not in options


async def test_custom_model_is_entered_inline_without_another_screen() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter", *"gpt-5.6", "down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert "Choose model" in str(picker.query_one("#model-picker-title", Static).render())
        options = str(picker.query_one("#model-options", Static).render())
        assert "openai-responses:gpt-5.6-sol" in options
        assert "Custom model" in options

        await pilot.press("enter")
        await pilot.pause()
        assert "provider:model" in str(picker.query_one("#model-options", Static).render())

        await pilot.press(*"test:model", "enter")
        await pilot.pause()
        assert app.screen is screen
        assert "test:model" in _text(screen, "#field-main-model")
