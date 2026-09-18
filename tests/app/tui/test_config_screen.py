from __future__ import annotations

from textual.app import App
from textual.content import Content
from textual.widgets import Static

from tabulaflow.app.config import LLMConfig, LLMRoleConfig, ResolvedLLMConfig
from tabulaflow.app.tui.screens.config import ConfigScreen, ModelPickerScreen


_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="openai:gpt-5.6-sol", effort="medium"),
    subagent=LLMRoleConfig(model="openai:gpt-5.4-mini", effort="low"),
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


def _option_text(screen: ModelPickerScreen) -> str:
    return str(screen.query_one("#model-options", Static).render())


async def test_config_screen_shows_role_fields_and_exact_identifiers() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert "‹ on ›" in _text(screen, "#field-enabled")
        assert "openai:gpt-5.6-sol" in _text(screen, "#field-main-model")
        assert "openai:gpt-5.4-mini" in _text(screen, "#field-subagent-model")
        assert _text(screen, "#field-main-model").endswith("openai:gpt-5.6-sol")
        assert _text(screen, "#field-subagent-model").endswith("openai:gpt-5.4-mini")
        assert "medium" in _text(screen, "#field-main-effort")
        assert "Subagent model" in _text(screen, "#field-subagent-model")
        assert "Effort" in _text(screen, "#field-main-effort")
        assert "Subagent effort" in _text(screen, "#field-subagent-effort")
        assert not list(screen.query("#config-credentials"))
        rendered = {str(widget.render()) for widget in screen.query(Static)}
        assert "MAIN AGENT" not in rendered
        assert "SUBAGENT" not in rendered


async def test_config_title_and_spacing_match_the_plain_style() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        title = screen.query_one("#config-title", Static).render()
        assert isinstance(title, Content)
        title_style = title.get_style_at_offset(0)
        assert title_style.bold
        assert title_style.foreground is None
        assert str(screen.query("#config-body > Static").nodes[1].render()) == ""


async def test_config_hint_omits_navigation_arrows() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        hint = _text(screen, "#config-hint")
        assert "Esc Back    " in hint
        assert "↑↓" not in hint
        assert "Navigate" not in hint
        assert "←→ Change" in hint
        await pilot.press("down")
        assert "Enter Change" in _text(screen, "#config-hint")


async def test_fields_are_edited_and_applied_atomically() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert "(recommended)" in _option_text(picker)
        assert not list(picker.query("#model-search"))
        await pilot.press("up", "enter")
        await pilot.pause()
        assert screen.dirty
        await pilot.press("escape")
        await pilot.pause()
        result = app.results[0]
        assert result is not None and result.config is not None
        assert result.config.main.model == "openai:gpt-5.6-terra"
        assert result.config.subagent == _CONFIG.subagent


async def test_disable_and_apply() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("enter", "escape")
        await pilot.pause()
        assert app.results == [ResolvedLLMConfig("off", None)]


async def test_disabled_llm_dims_and_skips_model_settings() -> None:
    screen = ConfigScreen(ResolvedLLMConfig("off", None))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "down")
        await pilot.pause()

        assert screen._cursor == 0
        assert app.screen is screen
        assert "❯ LLM" in _text(screen, "#field-enabled")
        for selector in ("#field-main-model", "#field-main-effort", "#field-subagent-model", "#field-subagent-effort"):
            rendered = screen.query_one(selector, Static).render()
            assert isinstance(rendered, Content)
            assert any(rendered.get_style_at_offset(index).dim for index in range(len(rendered)))


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
        assert "high" in _text(screen, "#field-main-effort")
        assert app.screen is screen
        await pilot.press("left", "escape")
        await pilot.pause()
        assert app.results == [None]


async def test_non_model_options_rotate() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("right")
        assert "‹ off ›" in _text(screen, "#field-enabled")
        await pilot.press("left")
        assert "‹ on ›" in _text(screen, "#field-enabled")

        await pilot.press("down", "down", "right", "right", "right")
        assert "minimal" in _text(screen, "#field-main-effort")
        await pilot.press("left")
        assert "xhigh" in _text(screen, "#field-main-effort")


async def test_model_picker_filters_without_search_input() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter", "a", "n", "t", "h")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert "“anth”" in str(picker.query_one("#model-picker-title", Static).render())
        options = _option_text(picker)
        assert "anthropic:" in options
        assert "openai:" not in options


async def test_model_picker_title_contains_guidance_and_uses_plain_bold() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        title = picker.query_one("#model-picker-title", Static).render()
        assert isinstance(title, Content)
        assert str(title) == "Choose model · Type to search or enter a custom model ID"
        title_style = title.get_style_at_offset(0)
        guidance_style = title.get_style_at_offset(-1)
        assert title_style.bold
        assert title_style.foreground is None
        assert guidance_style.dim
        assert not guidance_style.bold
        assert guidance_style.foreground is None
        hint = str(picker.query_one("#model-picker-hint", Static).render())
        assert "Navigate" not in hint
        assert "Type" not in hint

        await pilot.press("escape", "down", "down", "enter")
        await pilot.pause()
        assert str(app.screen.query_one("#model-picker-title", Static).render()).startswith("Choose subagent model")


async def test_filter_accepts_a_custom_model_identifier() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter", *"test:model")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = _option_text(picker)
        assert "Use test:model  (custom)" in options
        assert "“test:model”" in str(picker.query_one("#model-picker-title", Static).render())
        assert "Tab" not in str(picker.query_one("#model-picker-hint", Static).render())

        await pilot.press("enter")
        await pilot.pause()
        assert app.screen is screen
        assert "test:model" in _text(screen, "#field-main-model")


async def test_openai_chat_models_are_custom_only() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        model = "openai-chat:gpt-5.4-mini"
        await pilot.press("down", "enter", *model)
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert _option_text(picker).splitlines() == [f"❯ Use {model}  (custom)"]

        await pilot.press("enter")
        await pilot.pause()
        assert app.screen is screen
        assert model in _text(screen, "#field-main-model")


async def test_model_matches_are_selected_before_custom_identifier() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter", *"openai:gpt-5.6")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = _option_text(picker)
        assert "Use openai:gpt-5.6  (custom)" in options
        assert "openai:gpt-5.6-terra  (recommended)" in options
        assert "❯ openai:gpt-5.6-terra  (recommended)" in options

        await pilot.press("up", "enter")
        await pilot.pause()
        assert app.screen is screen
        assert "openai:gpt-5.6" in _text(screen, "#field-main-model")


async def test_no_matches_explains_custom_identifier_format() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter", *"not-a-model")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = _option_text(picker)
        assert "No matching models" in options
        assert "enter its full ID in provider:model format" in options


async def test_role_specific_recommendations() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = _option_text(picker)
        assert "openai:gpt-5.6-terra  (recommended)" in options
        assert "openai:gpt-5.6-sol  (recommended)" not in options

        await pilot.press("escape")
        await pilot.press("down", "down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = _option_text(picker)
        assert "openai:gpt-5.6-luna  (recommended)" in options
        assert "openai:gpt-5.4-mini  (recommended)" not in options


async def test_model_list_resizes_with_terminal() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test(size=(80, 18)) as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = picker.query_one("#model-options", Static)
        short_line_count = len(str(options.render()).splitlines())

        await pilot.resize_terminal(80, 40)

        assert len(str(options.render()).splitlines()) > short_line_count
