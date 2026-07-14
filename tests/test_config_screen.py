from __future__ import annotations

from types import SimpleNamespace
import pytest
from textual.app import App
from textual.widgets import Static

from tabulaflow.app.config import LLMRoleConfig, LLMPreset, ReasoningEffort
from tabulaflow.app.screens import ConfigScreen, LLMSelection

_PRESETS = [
    LLMPreset(
        label="OpenAI balanced",
        main=LLMRoleConfig(model="openai-responses:gpt-5.5", reasoning_effort="medium"),
        subagent=LLMRoleConfig(model="openai-responses:gpt-5.4-mini", reasoning_effort="medium"),
    ),
    LLMPreset(
        label="OpenAI budget",
        main=LLMRoleConfig(model="openai-responses:gpt-5.4-mini", reasoning_effort="medium"),
        subagent=LLMRoleConfig(model="openai-responses:gpt-5-mini", reasoning_effort="medium"),
    ),
    LLMPreset(
        label="Anthropic balanced",
        main=LLMRoleConfig(model="anthropic:claude-opus-4-8", reasoning_effort="high"),
        subagent=LLMRoleConfig(model="anthropic:claude-sonnet-4-5-20250929", reasoning_effort="high"),
    ),
    LLMPreset(
        label="Planning hybrid",
        main=LLMRoleConfig(model="anthropic:claude-opus-4-8", reasoning_effort="high"),
        subagent=LLMRoleConfig(model="openai-responses:gpt-5.4-mini", reasoning_effort="medium"),
    ),
]


class _StubSession:
    def __init__(
        self,
        label: str = "OpenAI balanced",
        model: str = "openai-responses:gpt-5.5",
        reasoning_effort: ReasoningEffort = "medium",
        subagent_model: str = "openai-responses:gpt-5.4-mini",
        subagent_reasoning_effort: ReasoningEffort = "medium",
    ) -> None:
        self.llm_preset: LLMPreset | None = LLMPreset(
            label=label,
            main=LLMRoleConfig(model=model, reasoning_effort=reasoning_effort),
            subagent=LLMRoleConfig(model=subagent_model, reasoning_effort=subagent_reasoning_effort),
        )


class _App(App[None]):
    def __init__(self, screen: ConfigScreen) -> None:
        super().__init__()
        self._config_screen = screen
        self.results: list[LLMSelection | None] = []

    def on_mount(self) -> None:
        self.push_screen(self._config_screen, self.results.append)


@pytest.fixture(autouse=True)
def _patch_config_io(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tabulaflow.app.screens.load_app_config",
        lambda: SimpleNamespace(llm_presets=list(_PRESETS)),
    )


def _row_plain(screen: ConfigScreen, i: int) -> str:
    return "".join(part.plain for part in screen._option_row_parts(i))


async def test_renders_presets() -> None:
    session = _StubSession()
    screen = ConfigScreen(session.llm_preset)
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert len(screen._option_rows) == 5
        assert screen._cursor == 1
        assert "LLM (main → subagent)" in {str(widget.render()) for widget in screen.query(Static)}
        assert "Off" in _row_plain(screen, 0)
        assert "Connect and browse data" in _row_plain(screen, 0)
        assert _row_plain(screen, 0).index("Connect and browse data") == 26
        assert "●" not in _row_plain(screen, 0)
        assert "●" in _row_plain(screen, 1)
        assert "OpenAI balanced" in _row_plain(screen, 1)
        assert "GPT 5.5 medium" in _row_plain(screen, 1)
        assert "GPT 5.4 Mini medium" in _row_plain(screen, 1)
        assert "OpenAI budget" in _row_plain(screen, 2)
        assert "GPT 5.4 Mini medium" in _row_plain(screen, 2)
        assert "GPT 5 Mini medium" in _row_plain(screen, 2)
        assert "Opus 4.8 high" in _row_plain(screen, 3)
        assert "Sonnet 4.5 high" in _row_plain(screen, 3)
        assert "Claude" not in _row_plain(screen, 3)
        assert "20250929" not in _row_plain(screen, 3)
        assert "Planning hybrid" in _row_plain(screen, 4)
        assert "Opus 4.8 high" in _row_plain(screen, 4)
        assert "GPT 5.4 Mini medium" in _row_plain(screen, 4)
        assert "●" not in _row_plain(screen, 2)
        assert all("API key" not in _row_plain(screen, i) for i in range(5))
        rows = [_row_plain(screen, i) for i in range(1, 5)]
        assert all(" · " not in row for row in rows)
        assert all(" → " in row for row in rows)
        assert {row.index(screen._option_row_parts(i)[2].plain) for i, row in enumerate(rows, start=1)} == {26}


async def test_preset_label_truncates_by_display_width_and_models_wrap_in_their_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_label_preset = _PRESETS[0].model_copy(update={"label": "分析プリセットの長い名前"})
    monkeypatch.setattr(
        "tabulaflow.app.screens.load_app_config",
        lambda: SimpleNamespace(llm_presets=[long_label_preset]),
    )
    screen = ConfigScreen(long_label_preset)

    async with _App(screen).run_test(size=(42, 24)) as pilot:
        await pilot.pause()
        _, label, _ = screen._option_row_parts(1)
        row = screen._option_rows[1]

        assert label.cell_len == 22
        assert label.plain.endswith("…  ")
        assert row._models.region.x == row.region.x + 26
        assert row.size.height > 1


async def test_enter_stages_selection_and_escape_returns_it() -> None:
    session = _StubSession()
    screen = ConfigScreen(session.llm_preset)
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "enter")
        assert app.screen is screen
        assert app.results == []
        assert session.llm_preset != _PRESETS[1]
        assert "●" in _row_plain(screen, 2)
        assert "●" not in _row_plain(screen, 1)

        await pilot.press("escape")
        await pilot.pause()
        assert app.results == [LLMSelection(_PRESETS[1])]


async def test_enter_stages_llm_off_until_escape() -> None:
    session = _StubSession()
    screen = ConfigScreen(session.llm_preset)
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("up", "enter")
        assert app.screen is screen
        assert app.results == []
        assert session.llm_preset is not None
        assert "●" in _row_plain(screen, 0)
        assert "●" not in _row_plain(screen, 1)

        await pilot.press("escape")
        await pilot.pause()
        assert app.results == [LLMSelection(None)]


async def test_llm_off_is_active_for_session_without_preset() -> None:
    session = _StubSession()
    session.llm_preset = None
    screen = ConfigScreen(session.llm_preset)

    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert screen._cursor == 0
        assert "● Off" in _row_plain(screen, 0)
        assert "Connect and browse data" in _row_plain(screen, 0)


async def test_multiple_selections_return_only_the_last_choice() -> None:
    session = _StubSession()
    screen = ConfigScreen(session.llm_preset)
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "enter", "down", "enter")
        assert app.results == []
        assert "●" in _row_plain(screen, 3)
        assert "●" not in _row_plain(screen, 2)
        await pilot.press("escape")
        await pilot.pause()
        assert app.results == [LLMSelection(_PRESETS[2])]


async def test_unverified_selected_preset_has_active_dot_without_error() -> None:
    session = _StubSession(
        label="Anthropic balanced",
        model="anthropic:claude-opus-4-8",
        reasoning_effort="high",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
        subagent_reasoning_effort="high",
    )
    screen = ConfigScreen(session.llm_preset)
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert len(screen._option_rows) == 5
        assert screen._cursor == 3
        row = _row_plain(screen, 3)
        assert "●" in row
        assert "LLM unavailable" not in row
        assert "Anthropic API key is not configured" not in row
        assert "ANTHROPIC_API_KEY" not in row
        assert "AnthropicProvider" not in row


async def test_current_custom_row_for_unmatched_runtime_profile() -> None:
    session = _StubSession(
        label="Test",
        model="openai-responses:gpt-5.5",
        reasoning_effort="high",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
        subagent_reasoning_effort="medium",
    )
    screen = ConfigScreen(session.llm_preset)
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(screen._option_rows) == 6
        assert screen._cursor == 1
        assert "● Current custom" in _row_plain(screen, 1)
        await pilot.press("enter")
        await pilot.press("down", "enter")
        assert app.results == []
        assert "●" in _row_plain(screen, 2)
        await pilot.press("escape")
        await pilot.pause()
        assert app.results == [LLMSelection(_PRESETS[0])]


async def test_select_preset_does_not_show_provider_error() -> None:
    session = _StubSession()
    screen = ConfigScreen(session.llm_preset)
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down", "enter")
        assert "Anthropic API key is not configured" not in _row_plain(screen, 3)
        assert "ANTHROPIC_API_KEY" not in _row_plain(screen, 3)
        assert "AnthropicProvider" not in _row_plain(screen, 3)
        assert "●" in _row_plain(screen, 3)
        assert "●" not in _row_plain(screen, 1)


async def test_escape_without_changed_selection_returns_no_result() -> None:
    session = _StubSession()
    screen = ConfigScreen(session.llm_preset)
    app = _App(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "enter", "up", "enter", "escape")
        await pilot.pause()
        assert app.results == [None]
