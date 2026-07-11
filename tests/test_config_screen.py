from __future__ import annotations

from typing import Any

import pytest
from textual.app import App

from tabulaflow.app.config import AppConfig, ModelOption
from tabulaflow.app.screens import ConfigScreen

_CATALOG = [
    ModelOption(
        model="openai-responses:gpt-5.4",
        label="GPT-5.4",
        efforts=("minimal", "low", "medium", "high"),
        default_effort="medium",
    ),
    ModelOption(model="test:limited", label="Limited", efforts=("low", "medium"), default_effort="medium"),
    ModelOption(model="anthropic:claude-sonnet-4-5-20250929", label="Claude Sonnet 4.5"),
]


class _StubSession:
    def __init__(self, model: str = "openai-responses:gpt-5.4", reasoning_effort: str = "medium") -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort

    def set_model(self, model: str) -> None:
        self.model = model

    def set_reasoning_effort(self, reasoning_effort: str) -> None:
        self.reasoning_effort = reasoning_effort


class _App(App[None]):
    def __init__(self, screen: ConfigScreen) -> None:
        super().__init__()
        self._config_screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._config_screen)


@pytest.fixture(autouse=True)
def _patch_config_io(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    monkeypatch.setattr("tabulaflow.app.screens.load_app_config", lambda: AppConfig(model_options=list(_CATALOG)))
    updates: list[dict[str, Any]] = []
    monkeypatch.setattr("tabulaflow.app.screens.update_app_config", lambda **prefs: updates.append(prefs))
    return updates


@pytest.fixture
def updates(_patch_config_io: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _patch_config_io


async def test_renders_catalog_with_nested_efforts() -> None:
    session = _StubSession()
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert len(screen._rows) == 3
        assert "●" in screen._render_row(0).plain
        assert "●" not in screen._render_row(1).plain
        assert screen._cursor == ("model", 0)  # starts on the current model
        # Effort chips render nested inside the active model's row only.
        assert "medium" in screen._render_row(0).plain
        assert "medium" not in screen._render_row(1).plain


async def test_enter_selects_model_and_persists(updates: list[dict[str, Any]]) -> None:
    session = _StubSession()
    refreshed: list[bool] = []
    screen = ConfigScreen(session, on_change=lambda: refreshed.append(True))  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down")  # over the effort row, onto model 1
        assert session.model == "openai-responses:gpt-5.4"  # browsing does not apply
        assert screen._cursor == ("model", 1)
        await pilot.press("enter")
        assert session.model == "test:limited"
        assert updates[-1]["model"] == "test:limited"
        assert refreshed
        # Effort chips moved under the newly active model.
        assert "medium" not in screen._render_row(0).plain
        assert "medium" in screen._render_row(1).plain


async def test_effort_kept_when_supported(updates: list[dict[str, Any]]) -> None:
    session = _StubSession(reasoning_effort="low")
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down", "enter")  # "low" is valid for test:limited
        assert session.reasoning_effort == "low"


async def test_effort_snaps_to_default_when_unsupported(updates: list[dict[str, Any]]) -> None:
    session = _StubSession(reasoning_effort="high")
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down", "enter")  # "high" invalid for test:limited
        assert session.reasoning_effort == "medium"
        assert updates[-1] == {"model": "test:limited", "reasoning_effort": "medium"}


async def test_effort_retained_when_not_applicable(updates: list[dict[str, Any]]) -> None:
    session = _StubSession(reasoning_effort="high")
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down", "down", "enter")  # Claude: no efforts
        assert session.reasoning_effort == "high"  # preference retained
        # No effort chips anywhere: the row simply isn't there.
        assert all("high" not in screen._render_row(i).plain for i in range(3))
        # Cursor stops at the last model row.
        await pilot.press("down", "down")
        assert screen._cursor == ("model", 2)


async def test_cycle_reasoning(updates: list[dict[str, Any]]) -> None:
    session = _StubSession()
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down")  # onto the effort row nested under the active model
        assert screen._cursor == ("effort", 0)
        await pilot.press("right")
        assert session.reasoning_effort == "high"
        await pilot.press("right")  # wraps around
        assert session.reasoning_effort == "minimal"
        # Left/right on a model row does nothing.
        await pilot.press("up", "left")
        assert session.reasoning_effort == "minimal"
        # Enter on the effort row does nothing.
        await pilot.press("down", "enter")
        assert session.model == "openai-responses:gpt-5.4"


async def test_select_failure_shows_inline_error(updates: list[dict[str, Any]]) -> None:
    class _FailingSession(_StubSession):
        def set_model(self, model: str) -> None:
            if model.startswith("anthropic:"):
                raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
            self.model = model

    session = _FailingSession()
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down", "down", "enter")  # attempt Claude
        assert session.model == "openai-responses:gpt-5.4"  # previous model kept
        assert not updates  # nothing persisted
        assert "ANTHROPIC_API_KEY" in screen._render_row(2).plain
        assert "●" in screen._render_row(0).plain  # active marker unmoved
        # Error survives browsing but clears on the next select.
        await pilot.press("up")
        assert "ANTHROPIC_API_KEY" in screen._render_row(2).plain
        await pilot.press("enter")  # select test:limited — succeeds
        assert session.model == "test:limited"
        assert "ANTHROPIC_API_KEY" not in screen._render_row(2).plain


async def test_unlisted_model_prepended_with_fallback() -> None:
    session = _StubSession(model="together:custom/model")
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert screen._options[0].model == "together:custom/model"
        assert screen._options[0].efforts == ()
        assert len(screen._rows) == 4
