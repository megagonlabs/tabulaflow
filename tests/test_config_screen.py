from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from textual.app import App

from tabulaflow.app.config import ModelOption
from tabulaflow.app.screens import ConfigScreen

_CATALOG = [
    ModelOption(model="openai-responses:gpt-5.5", label="GPT-5.5", recommended_effort="medium"),
    ModelOption(model="anthropic:claude-opus-4-8", label="Claude Opus 4.8", recommended_effort="high"),
    ModelOption(model="test:no-thinking", label="No Thinking"),
]

_SUBAGENT_CATALOG = [
    ModelOption(model="openai-responses:gpt-5.4-mini", label="GPT-5.4 Mini", recommended_effort="medium"),
    ModelOption(model="anthropic:claude-sonnet-4-5-20250929", label="Claude Sonnet 4.5", recommended_effort="high"),
]

_EFFORTS = ("low", "medium", "high", "xhigh")


class _StubSession:
    """Session stub: thinking support keyed by the active model, like the real
    profile-derived property."""

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

    @property
    def supported_efforts(self) -> tuple[str, ...]:
        return () if self.model.startswith("test:") else _EFFORTS

    @property
    def subagent_supported_efforts(self) -> tuple[str, ...]:
        return () if self.subagent_model.startswith("test:") else _EFFORTS

    def set_model(self, model: str) -> None:
        self.model = model

    def set_reasoning_effort(self, reasoning_effort: str) -> None:
        self.reasoning_effort = reasoning_effort

    def set_subagent_model(self, model: str) -> None:
        self.subagent_model = model

    def set_subagent_reasoning_effort(self, reasoning_effort: str) -> None:
        self.subagent_reasoning_effort = reasoning_effort


class _App(App[None]):
    def __init__(self, screen: ConfigScreen) -> None:
        super().__init__()
        self._config_screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._config_screen)


@pytest.fixture(autouse=True)
def _patch_config_io(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    # The screen reads only the model catalogs off the loaded config; hand it
    # fixed catalogs directly (the real fields are custom-option merges).
    monkeypatch.setattr(
        "tabulaflow.app.screens.load_app_config",
        lambda: SimpleNamespace(
            model_options=list(_CATALOG),
            subagent_model_options=list(_SUBAGENT_CATALOG),
        ),
    )
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
        assert len(screen._subagent_rows) == 2
        assert "●" in screen._render_row(0).plain
        assert "●" not in screen._render_row(1).plain
        assert "●" in screen._render_subagent_row(0).plain
        assert screen._subagent_options[0].model == "openai-responses:gpt-5.4-mini"
        assert screen._subagent_options[1].model == "anthropic:claude-sonnet-4-5-20250929"
        assert screen._cursor == ("model", 0)  # starts on the current model
        # Effort chips render nested inside the active model's row only, with
        # the sourced vendor recommendation tagged.
        assert "medium (recommended)" in screen._render_row(0).plain
        assert "xhigh" in screen._render_row(0).plain
        assert "medium" not in screen._render_row(1).plain
        assert "medium (recommended)" in screen._render_subagent_row(0).plain
        assert "effort:" not in screen._render_subagent_row(1).plain


async def test_enter_selects_model_and_persists(updates: list[dict[str, Any]]) -> None:
    session = _StubSession()
    refreshed: list[bool] = []
    screen = ConfigScreen(session, on_change=lambda: refreshed.append(True))  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down")  # over the effort row, onto model 1
        assert session.model == "openai-responses:gpt-5.5"  # browsing does not apply
        assert screen._cursor == ("model", 1)
        await pilot.press("enter")
        assert session.model == "anthropic:claude-opus-4-8"
        assert updates[-1]["model"] == "anthropic:claude-opus-4-8"
        assert refreshed
        # Effort snapped to the new model's recommendation, chips moved under
        # it, and the cursor advanced onto them so ←→ tunes immediately.
        assert session.reasoning_effort == "high"
        assert updates[-1]["reasoning_effort"] == "high"
        assert "high (recommended)" in screen._render_row(1).plain
        assert "medium" not in screen._render_row(0).plain
        assert screen._cursor == ("effort", 1)
        await pilot.press("left")
        assert session.reasoning_effort == "medium"


async def test_effort_snaps_to_recommendation_on_switch(updates: list[dict[str, Any]]) -> None:
    session = _StubSession(reasoning_effort="xhigh")
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down", "enter")  # switch to Claude
        assert session.reasoning_effort == "high"  # Claude's recommendation


async def test_reselecting_active_model_keeps_effort(updates: list[dict[str, Any]]) -> None:
    session = _StubSession(reasoning_effort="xhigh")  # deliberate, above GPT's recommendation
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # re-select the already-active model
        assert session.reasoning_effort == "xhigh"  # not reset to "medium"


async def test_no_chips_for_non_thinking_model(updates: list[dict[str, Any]]) -> None:
    session = _StubSession(reasoning_effort="high")
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down", "down", "enter")  # test:no-thinking
        assert session.reasoning_effort == "high"  # preference retained
        assert all("effort:" not in screen._render_row(i).plain for i in range(3))
        # Effort row unreachable: cursor stays on the model row after select.
        # The next reachable row is the subagent model section.
        assert screen._cursor == ("model", 2)
        await pilot.press("down")
        assert screen._cursor == ("subagent_model", 0)


async def test_cycle_reasoning(updates: list[dict[str, Any]]) -> None:
    session = _StubSession()
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down")  # onto the effort row nested under the active model
        assert screen._cursor == ("effort", 0)
        await pilot.press("right", "right")
        assert session.reasoning_effort == "xhigh"
        await pilot.press("right")  # wraps around
        assert session.reasoning_effort == "low"
        # Left/right on a model row does nothing.
        await pilot.press("up", "left")
        assert session.reasoning_effort == "low"
        # Enter on the effort row does nothing.
        await pilot.press("down", "enter")
        assert session.model == "openai-responses:gpt-5.5"


async def test_provider_and_api_key_suffixes() -> None:
    session = _StubSession()
    session.api_key = "sk-test123456789ab4x"
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        # Provider (not the full id) on every catalog row.
        assert "· openai-responses" in screen._render_row(0).plain
        assert "openai-responses:gpt-5.5" not in screen._render_row(0).plain
        assert "· anthropic" in screen._render_row(1).plain
        # Masked key on the active row only.
        assert "API key sk-***ab4x" in screen._render_row(0).plain
        assert "API key" not in screen._render_row(1).plain
        session.subagent_api_key = "sk-sub123456789cd9y"
        assert "API key sk-***cd9y" in screen._render_subagent_row(0).plain
        assert "API key" not in screen._render_subagent_row(1).plain


async def test_api_key_suffix_omitted_when_unavailable() -> None:
    session = _StubSession()  # api_key None (e.g. ADC or unrecognized client)
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert "API key" not in screen._render_row(0).plain
        assert "API key" not in screen._render_subagent_row(0).plain


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
        await pilot.press("down", "down", "enter")  # attempt Claude
        assert session.model == "openai-responses:gpt-5.5"  # previous model kept
        assert not updates  # nothing persisted
        assert "ANTHROPIC_API_KEY" in screen._render_row(1).plain
        assert "●" in screen._render_row(0).plain  # active marker unmoved
        # Error survives browsing but clears on the next select.
        await pilot.press("down")
        assert "ANTHROPIC_API_KEY" in screen._render_row(1).plain
        await pilot.press("enter")  # select test:no-thinking — succeeds
        assert session.model == "test:no-thinking"
        assert "ANTHROPIC_API_KEY" not in screen._render_row(1).plain


async def test_enter_selects_subagent_model_and_persists(updates: list[dict[str, Any]]) -> None:
    session = _StubSession()
    refreshed: list[bool] = []
    screen = ConfigScreen(session, on_change=lambda: refreshed.append(True))  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "down", "down", "down", "down", "down")  # into subagent section, model 1
        assert screen._cursor == ("subagent_model", 1)
        await pilot.press("enter")
        assert session.model == "openai-responses:gpt-5.5"
        assert session.subagent_model == "anthropic:claude-sonnet-4-5-20250929"
        assert session.subagent_reasoning_effort == "high"
        assert updates[-1]["model"] == "openai-responses:gpt-5.5"
        assert updates[-1]["subagent_model"] == "anthropic:claude-sonnet-4-5-20250929"
        assert updates[-1]["subagent_reasoning_effort"] == "high"
        assert refreshed
        assert "●" in screen._render_subagent_row(1).plain
        assert screen._cursor == ("subagent_effort", 1)
        await pilot.press("left")
        assert session.subagent_reasoning_effort == "medium"


async def test_unlisted_model_prepended() -> None:
    session = _StubSession(model="together:custom/model")
    screen = ConfigScreen(session, on_change=lambda: None)  # type: ignore[arg-type]
    async with _App(screen).run_test() as pilot:
        await pilot.pause()
        assert screen._options[0].model == "together:custom/model"
        assert len(screen._rows) == 4
        # Label is already the full id — no provider suffix repeated after it.
        assert "· together" not in screen._render_row(0).plain
