from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from textual.app import App
from textual.content import Content
from textual.screen import Screen
from textual.style import Style
from textual.widgets import Input, Static

from tabulaflow.app.config import CredentialPreference, LLMConfig, LLMRoleConfig, ResolvedLLMConfig
from tabulaflow.app.credentials import APIKeyStore
from tabulaflow.app.model_catalog import VLLMDiscoveryResult, VLLMModelDiscovery
from tabulaflow.app.providers import provider_spec
from tabulaflow.app.tui.screens.config import ConfigScreen, ModelPickerScreen
from tabulaflow.app.tui.screens.providers import APIKeyScreen, ProviderPickerScreen
from tabulaflow.app.tui.theme import ACCENT_BOLD

_TEST_MODEL_CATALOG = (
    "openai:gpt-6-astra",
    "anthropic:claude-sonnet-5",
    *(f"openai:model-{index}" for index in range(40)),
)


@pytest.fixture(autouse=True)
def _stub_local_model_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    async def test_catalog() -> tuple[str, ...]:
        return _TEST_MODEL_CATALOG

    monkeypatch.setattr("tabulaflow.app.tui.screens.config.load_local_model_catalog", test_catalog)


_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="openai:gpt-5.6-sol", effort="medium"),
    subagent=LLMRoleConfig(model="openai:gpt-5.4-mini", effort="low"),
)


class _VLLMDiscovery(VLLMModelDiscovery):
    def __init__(
        self,
        *,
        base_url: str = "",
        result: VLLMDiscoveryResult | None = None,
        endpoint_label: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.endpoint_label = endpoint_label
        self._result = result

    def result(self) -> VLLMDiscoveryResult | None:
        return self._result

    async def warm(self) -> VLLMDiscoveryResult | None:
        return self._result


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
    provider_action = str(screen.query_one("#change-provider", Static).render())
    provider = str(screen.query_one("#model-provider", Static).render())
    options = str(screen.query_one("#model-options", Static).render()).rstrip("\n")
    return f"{provider_action}\n{provider}\n{options}"


def _active_screen(app: App[None]) -> Screen[object]:
    return app.screen


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
        assert "Max model requests/min" in _text(screen, "#field-requests-per-minute")
        assert "300 RPM" in _text(screen, "#field-requests-per-minute")
        assert "requests/min    ‹" in _text(screen, "#field-requests-per-minute")
        assert not list(screen.query("#config-credentials"))
        rendered = {str(widget.render()) for widget in screen.query(Static)}
        assert "MAIN AGENT" not in rendered
        assert "SUBAGENT" not in rendered


async def test_request_rate_cycles_through_presets() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "down", "down", "down", "down", "right", "escape")
        await pilot.pause()

    result = app.results[0]
    assert result is not None and result.config is not None
    assert result.config.requests_per_minute == 600


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
        await pilot.press("down", "enter")
        await pilot.pause()
        assert screen.dirty
        await pilot.press("escape")
        await pilot.pause()
        result = app.results[0]
        assert result is not None and result.config is not None
        assert result.config.main.model == "openai:gpt-6-astra"
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
        await pilot.press("down", "enter", *"astra")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert "“astra”" in str(picker.query_one("#model-picker-title", Static).render())
        options = _option_text(picker)
        assert "gpt-6-astra" in options
        assert "openai:" not in options
        assert "anthropic:" not in options
        assert "Use another provider" in options


async def test_model_picker_loads_only_available_models_from_current_provider() -> None:
    async def available_catalog() -> tuple[str, ...]:
        return ("fireworks:accounts/fireworks/models/kimi-k3", "anthropic:claude-sonnet-5")

    picker = ModelPickerScreen(
        "main",
        "fireworks:accounts/fireworks/models/glm-5p3",
        catalog_loader=available_catalog,
    )

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(picker)

    async with PickerApp().run_test() as pilot:
        await pilot.pause()
        options = _option_text(picker)
        assert "accounts/fireworks/models/kimi-k3" in options
        assert "fireworks:" not in options
        assert "anthropic:" not in options


async def test_long_model_ids_stay_on_one_line_and_preserve_the_full_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = "fireworks:accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b"

    async def available_catalog() -> tuple[str, ...]:
        return (model, *(f"fireworks:model-{index}" for index in range(30)))

    picker = ModelPickerScreen(
        "main",
        model,
        catalog_loader=available_catalog,
        vllm_discovery=_VLLMDiscovery(),
    )
    selected: list[str | None] = []
    catalog_rendered = asyncio.Event()
    original_refresh = picker._refresh

    def track_refresh() -> None:
        original_refresh()
        if picker.size.width == 60 and "fireworks:model-29" in picker._models:
            catalog_rendered.set()

    monkeypatch.setattr(picker, "_refresh", track_refresh)

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(picker, selected.append)

    async with PickerApp().run_test(size=(60, 18)) as pilot:
        await asyncio.wait_for(catalog_rendered.wait(), timeout=2)
        options = _option_text(picker)
        assert model not in options
        assert "❯ ● …" in options
        assert "nemotron-lightning-3p5-30b-a3b" in options
        assert "↓" in options
        assert all(len(line) <= 54 for line in options.splitlines())

        await pilot.press("enter")
        await pilot.pause()

    assert selected == [model]


async def test_model_picker_marks_the_current_model_independently_of_the_cursor() -> None:
    current = "fireworks:accounts/fireworks/models/kimi-k3"
    alternative = "fireworks:accounts/fireworks/models/glm-5p3"

    async def available_catalog() -> tuple[str, ...]:
        return (current, alternative)

    picker = ModelPickerScreen("main", current, catalog_loader=available_catalog)

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(picker)

    async with PickerApp().run_test() as pilot:
        await pilot.pause()
        await pilot.press("down")
        options = _option_text(picker)

    assert "  ● accounts/fireworks/models/kimi-k3" in options
    assert "❯   accounts/fireworks/models/glm-5p3" in options


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
        assert str(title) == "Choose main model · Type to filter"
        title_style = title.get_style_at_offset(0)
        guidance_style = title.get_style_at_offset(-1)
        assert title_style.bold
        assert title_style.foreground is None
        assert guidance_style.dim
        assert not guidance_style.bold
        assert guidance_style.foreground is None
        assert picker.query_one("#change-provider", Static).styles.margin.bottom == 0
        provider_widget = picker.query_one("#model-provider", Static)
        provider = provider_widget.render()
        assert isinstance(provider, Content)
        assert str(provider) == "    Current provider: OpenAI"
        assert provider.spans[0].style == "dim"
        assert provider_widget.styles.margin.bottom == 0
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


async def test_model_picker_explains_how_to_enable_vllm_discovery() -> None:
    discovery = _VLLMDiscovery()
    picker = ModelPickerScreen("main", "vllm:Qwen/Qwen3-8B", vllm_discovery=discovery)

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(picker)

    async with PickerApp().run_test() as pilot:
        await pilot.pause()
        options = _option_text(picker)
        assert "\n\n\n  vLLM · set VLLM_BASE_URL to discover models" in options


async def test_model_picker_lists_discovered_vllm_models() -> None:
    discovery = _VLLMDiscovery(
        base_url="http://localhost:8000/v1",
        result=VLLMDiscoveryResult(models=("vllm:Qwen/Qwen3-8B",)),
        endpoint_label="localhost:8000/v1",
    )
    picker = ModelPickerScreen("main", "vllm:Qwen/Qwen3-8B", vllm_discovery=discovery)

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(picker)

    async with PickerApp().run_test() as pilot:
        await pilot.pause()
        options = _option_text(picker)
        assert "Qwen/Qwen3-8B" in options
        assert "vllm:" not in options
        assert "openai:" not in options
        await pilot.press(*"vllm")
        assert "Qwen/Qwen3-8B" in _option_text(picker)


async def test_model_picker_surfaces_vllm_discovery_failure() -> None:
    discovery = _VLLMDiscovery(
        base_url="http://localhost:8000/v1",
        result=VLLMDiscoveryResult(error="no valid vLLM models API found — check VLLM_BASE_URL"),
        endpoint_label="localhost:8000/v1",
    )
    picker = ModelPickerScreen("main", "vllm:Qwen/Qwen3-8B", vllm_discovery=discovery)

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(picker)

    async with PickerApp().run_test() as pilot:
        await pilot.pause()
        assert "vLLM · localhost:8000/v1: no valid vLLM models API found — check VLLM_BASE_URL" in _option_text(picker)


async def test_openai_chat_models_are_custom_only() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        model = "openai-chat:gpt-5.4-mini"
        await pilot.press("down", "enter", *model)
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert _option_text(picker).splitlines() == [
            "    Use another provider",
            "    Current provider: OpenAI",
            f"❯   Use {model}  (custom)",
        ]

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
        assert "gpt-5.6-sol  (recommended)" in options
        assert "❯ ● gpt-5.6-sol  (recommended)" in options

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
        assert "custom model ID in provider:model format" in options
        assert "Use another provider" in options


async def test_role_specific_recommendations() -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = _option_text(picker)
        assert "gpt-5.6-sol  (recommended)" in options
        assert "gpt-6-sol  (recommended)" not in options
        assert "gpt-5.6-terra  (recommended)" not in options

        await pilot.press("escape")
        await pilot.press("down", "down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = _option_text(picker)
        assert "gpt-6-sol  (recommended)" in options
        assert "gpt-5.6-luna  (recommended)" in options
        assert "gpt-6-luna  (recommended)" not in options
        assert "gpt-5.4-mini  (recommended)" not in options


async def test_model_list_resizes_with_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG))
    app = _App(screen)
    async with app.run_test(size=(80, 18)) as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        options = picker.query_one("#model-options", Static)
        short_line_count = len(str(options.render()).splitlines())
        resize_rendered = asyncio.Event()
        original_refresh = picker._refresh

        def track_refresh() -> None:
            original_refresh()
            if picker.size.height == 40:
                resize_rendered.set()

        monkeypatch.setattr(picker, "_refresh", track_refresh)

        await pilot.resize_terminal(80, 40)
        await asyncio.wait_for(resize_rendered.wait(), timeout=2)

        assert len(str(options.render()).splitlines()) > short_line_count


async def test_long_configured_model_fits_the_config_field_and_expands_on_resize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = "fireworks:accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b"
    config = _CONFIG.model_copy(deep=True)
    config.main.model = model
    screen = ConfigScreen(ResolvedLLMConfig(config, config))

    async with _App(screen).run_test(size=(60, 18)) as pilot:
        await pilot.pause()
        compact = _text(screen, "#field-main-model")
        assert model not in compact
        assert "fireworks:…" in compact
        assert compact.endswith("3p5-30b-a3b")
        assert len(compact.splitlines()) == 1
        resize_rendered = asyncio.Event()
        original_refresh = screen._refresh

        def track_refresh() -> None:
            original_refresh()
            if screen.size.width == 120:
                resize_rendered.set()

        monkeypatch.setattr(screen, "_refresh", track_refresh)

        await pilot.resize_terminal(120, 18)
        await asyncio.wait_for(resize_rendered.wait(), timeout=2)

        assert model in _text(screen, "#field-main-model")


async def test_provider_picker_lists_only_provider_names() -> None:
    picker = ProviderPickerScreen("openai")

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(picker)

    async with PickerApp().run_test() as pilot:
        await pilot.pause()
        rendered = picker.query_one("#provider-options", Static).render()
        assert isinstance(rendered, Content)
        options = str(rendered)
        assert options.splitlines()[:2] == ["❯ OpenAI", "  Anthropic"]
        assert " · " not in options
        assert all(rendered.get_style_at_offset(index) == Style.parse(ACCENT_BOLD) for index in (0, 2))


async def test_connection_screen_offers_both_sources_even_with_identical_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-shared-secret")
    store = APIKeyStore(tmp_path / "credentials.json")
    store.save("OPENAI_API_KEY", "sk-shared-secret")
    auth = APIKeyScreen(
        provider_spec("openai"),
        credential_store=store,
        preferred_saved_variable="OPENAI_API_KEY",
    )

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(auth)

    async with PickerApp().run_test() as pilot:
        await pilot.pause()
        options = str(auth.query_one("#api-key-options", Static).render())
        paste = str(auth.query_one("#api-key-paste-label", Static).render())
        assert options.splitlines() == [
            "    Use environment OPENAI_API_KEY (sk-***cret)",
            "",
            "❯ ● Use saved OPENAI_API_KEY (sk-***cret)",
        ]
        assert paste == "    Paste API key"
        assert auth._cursor == 1


async def test_saved_key_loaded_into_environment_is_not_a_second_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-saved-secret")
    store = APIKeyStore(tmp_path / "credentials.json")
    store.save("OPENAI_API_KEY", "sk-saved-secret")
    auth = APIKeyScreen(
        provider_spec("openai"),
        credential_store=store,
        environment_credentials={"OPENAI_API_KEY": ""},
    )

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(auth)

    async with PickerApp().run_test() as pilot:
        await pilot.pause()
        options = str(auth.query_one("#api-key-options", Static).render())
        assert options == "❯ ● Use saved OPENAI_API_KEY (sk-***cret)"
        assert "Use environment" not in options


async def test_provider_switch_uses_detected_key_and_updates_only_selected_role(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-test")
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: None)
    screen = ConfigScreen(
        ResolvedLLMConfig(_CONFIG, _CONFIG),
        credential_store=APIKeyStore(tmp_path / "credentials.json"),
    )
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        assert picker._cursor > 0
        await pilot.press("up", "enter")
        await pilot.pause()
        assert isinstance(app.screen, ProviderPickerScreen)

        await pilot.press(*"anthropic", "enter")
        await pilot.pause()
        auth = app.screen
        assert isinstance(auth, APIKeyScreen)
        options_widget = auth.query_one("#api-key-options", Static)
        rendered = options_widget.render()
        assert isinstance(rendered, Content)
        options = str(rendered)
        assert "Use environment ANTHROPIC_API_KEY (sk-***test)" in options
        assert not options.endswith("\n\n")
        assert all(rendered.get_style_at_offset(index) == Style.parse(ACCENT_BOLD) for index in (0, 2, 4))
        paste = auth.query_one("#api-key-paste")
        assert paste.styles.margin.top == 1
        assert paste.region.y == options_widget.region.y + options_widget.region.height + 1
        key_input = auth.query_one("#api-key-input", Input)
        assert not key_input.has_focus
        await pilot.press("down")
        await pilot.pause()
        assert key_input.has_focus
        paste_label = auth.query_one("#api-key-paste-label", Static).render()
        assert isinstance(paste_label, Content)
        assert str(paste_label).startswith("❯   Paste API key")
        assert all(paste_label.get_style_at_offset(index) == Style.parse(ACCENT_BOLD) for index in (0, 4))
        await pilot.press("up")
        await pilot.pause()
        assert not key_input.has_focus
        await pilot.press("enter")
        await pilot.pause()

        assert _active_screen(app) == picker
        options = _option_text(picker)
        assert "claude-sonnet-5" in options
        assert "anthropic:" not in options
        assert "openai:" not in options
        assert picker._cursor == 1
        await pilot.press("enter")
        await pilot.pause()
        assert _active_screen(app) == screen
        await pilot.press("escape")
        await pilot.pause()

    result = app.results[0]
    assert result is not None and result.config is not None
    assert result.config.main.model == "anthropic:claude-sonnet-5"
    assert result.config.subagent == _CONFIG.subagent


async def test_pasted_key_is_masked_saved_and_applied_with_unchanged_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: None)
    store = APIKeyStore(tmp_path / "credentials.json")
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG), credential_store=store)
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        picker._cursor = 0
        await pilot.press("enter", "enter")
        await pilot.pause()

        auth = app.screen
        assert isinstance(auth, APIKeyScreen)
        key_input = auth.query_one("#api-key-input", Input)
        assert key_input.display
        assert key_input.password
        assert key_input.parent == auth.query_one("#api-key-paste")
        assert not auth.query_one("#api-key-options", Static).display
        assert auth.query_one("#api-key-paste").styles.margin.top == 0
        assert "Paste API key" in str(auth.query_one("#api-key-paste-label", Static).render())
        assert "credentials.json" not in str(auth.query_one("#api-key-status", Static).render())
        assert key_input.has_focus
        assert str(auth.query_one("#api-key-paste-label", Static).render()).startswith("❯   Paste API key")
        await pilot.press(*"sk-pasted-secret")
        assert "sk-pasted-secret" not in str(key_input.render())
        await pilot.press("enter")
        await pilot.pause()

        assert store.get("OPENAI_API_KEY") == "sk-pasted-secret"
        assert os.environ["OPENAI_API_KEY"] == "sk-pasted-secret"
        assert _active_screen(app) == picker
        await pilot.press("enter")
        await pilot.pause()
        assert screen.dirty
        await pilot.press("escape")
        await pilot.pause()

    result = app.results[0]
    assert result is not None and result.config == _CONFIG
    assert result.credential_preferences == {"openai": CredentialPreference(source="saved", variable="OPENAI_API_KEY")}


async def test_cancelling_model_picker_after_key_change_still_applies_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-original-secret")
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: None)
    store = APIKeyStore(tmp_path / "credentials.json")
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG), credential_store=store)
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        picker._cursor = 0
        await pilot.press("enter", "enter", "down", *"sk-replacement-secret", "enter")
        await pilot.pause()

        assert store.get("OPENAI_API_KEY") == "sk-replacement-secret"
        assert os.environ["OPENAI_API_KEY"] == "sk-replacement-secret"
        assert _active_screen(app) == picker
        await pilot.press("escape")
        await pilot.pause()
        assert _active_screen(app) == screen
        assert screen.dirty
        await pilot.press("escape")
        await pilot.pause()

    result = app.results[0]
    assert result is not None and result.config == _CONFIG
    assert result.credential_preferences == {"openai": CredentialPreference(source="saved", variable="OPENAI_API_KEY")}


async def test_saved_key_can_be_selected_explicitly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: None)
    store = APIKeyStore(tmp_path / "credentials.json")
    store.save("ANTHROPIC_API_KEY", "sk-saved-secret")
    screen = ConfigScreen(ResolvedLLMConfig(_CONFIG, _CONFIG), credential_store=store)
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        picker._cursor = 0
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press(*"anthropic", "enter")
        await pilot.pause()

        auth = app.screen
        assert isinstance(auth, APIKeyScreen)
        options = str(auth.query_one("#api-key-options", Static).render())
        assert "Use saved ANTHROPIC_API_KEY" in options
        assert "sk-saved-secret" not in options
        await pilot.press("enter")
        await pilot.pause()
        assert os.environ["ANTHROPIC_API_KEY"] == "sk-saved-secret"
        assert _active_screen(app) == picker
        assert picker.credential_preferences == {
            "anthropic": CredentialPreference(source="saved", variable="ANTHROPIC_API_KEY")
        }


async def test_environment_selection_restores_automatic_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-saved-secret")
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: None)
    store = APIKeyStore(tmp_path / "credentials.json")
    store.save("OPENAI_API_KEY", "sk-saved-secret")
    preference = CredentialPreference(source="saved", variable="OPENAI_API_KEY")
    screen = ConfigScreen(
        ResolvedLLMConfig(
            _CONFIG,
            _CONFIG,
            credential_preferences={"openai": preference},
            environment_credentials={"OPENAI_API_KEY": "sk-environment-secret"},
        ),
        credential_store=store,
    )
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        picker._cursor = 0
        await pilot.press("enter", "enter", "up", "enter")
        await pilot.pause()
        assert os.environ["OPENAI_API_KEY"] == "sk-environment-secret"
        assert _active_screen(app) == picker
        assert picker.credential_preferences == {}
        await pilot.press("escape", "escape")
        await pilot.pause()

    result = app.results[0]
    assert result is not None and result.credential_preferences == {}
    assert result.environment_credentials == {"OPENAI_API_KEY": "sk-environment-secret"}


async def test_cancelling_provider_or_key_selection_preserves_configuration(tmp_path: Path) -> None:
    screen = ConfigScreen(
        ResolvedLLMConfig(_CONFIG, _CONFIG),
        credential_store=APIKeyStore(tmp_path / "credentials.json"),
    )
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        await pilot.pause()
        picker = app.screen
        assert isinstance(picker, ModelPickerScreen)
        picker._cursor = 0
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ProviderPickerScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert _active_screen(app) == picker
        assert picker._provider == "openai"

        picker._cursor = 0
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter", "escape")
        await pilot.pause()
        assert _active_screen(app) == picker
        assert not screen.dirty
        await pilot.press("escape")
        await pilot.pause()
        assert _active_screen(app) == screen
        await pilot.press("escape")
        await pilot.pause()

    assert app.results == [None]


async def test_local_provider_switch_skips_api_key_screen(tmp_path: Path) -> None:
    discovery = _VLLMDiscovery(result=VLLMDiscoveryResult(models=("vllm:Qwen/Qwen3-8B",)))
    picker = ModelPickerScreen(
        "main",
        _CONFIG.main.model,
        vllm_discovery=discovery,
        credential_store=APIKeyStore(tmp_path / "credentials.json"),
    )

    class PickerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(picker)

    app = PickerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        picker._cursor = 0
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press(*"vllm", "enter")
        await pilot.pause()

        assert _active_screen(app) == picker
        assert picker._provider == "vllm"
        assert "Qwen/Qwen3-8B" in _option_text(picker)
        assert "Current provider: vLLM" in str(picker.query_one("#model-provider", Static).render())
