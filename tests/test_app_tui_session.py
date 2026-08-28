from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from textual import events
from textual.containers import VerticalScroll
from textual.widgets import Button, Input, Static

from tabulaflow.app import session as session_module
from tabulaflow.app.tui import app as tui
from tabulaflow.app.tui.commands import CommandResult
from tabulaflow.app.config import LLM_OFF, LLMRoleConfig, LLMPreset, ReasoningEffort, ResolvedLLMSelection
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.session import AppSession
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.app.tui.widgets.chat import BannerWidget, SpinnerWidget, SystemMessage, UserMessage
from tabulaflow.app.tui.widgets.input import HistoryInput

if TYPE_CHECKING:
    from tabulaflow.agents.chat import ChatSession


class _StatusCapture:
    def __init__(self) -> None:
        self.value = ""

    def update(self, value: object) -> None:
        self.value = str(value)


class _InactiveSession:
    selected_preset: LLMPreset | None = None

    def select_llm_preset(self, preset: LLMPreset | None) -> None:
        self.selected_preset = preset

    def activate_llm_preset(self, preset: LLMPreset | None) -> tuple[None, None]:
        return None, None


def _preset(
    *,
    label: str = "Test",
    model: str = "test",
    reasoning_effort: ReasoningEffort = "low",
    subagent_model: str = "test",
    subagent_reasoning_effort: ReasoningEffort = "medium",
) -> LLMPreset:
    return LLMPreset(
        label=label,
        main=LLMRoleConfig(model=model, reasoning_effort=reasoning_effort),
        subagent=LLMRoleConfig(model=subagent_model, reasoning_effort=subagent_reasoning_effort),
    )


def _selection(
    preset: LLMPreset | None,
    *,
    inferred: bool = False,
    detected_api_key_env: str | None = None,
) -> ResolvedLLMSelection:
    selection = None if inferred else (preset.label if preset is not None else LLM_OFF)
    return ResolvedLLMSelection(selection, preset, detected_api_key_env)


def _app_for_selection(
    selection: ResolvedLLMSelection,
    *,
    runtime_paths: RuntimePaths | None = None,
    project_dir: Path | None = None,
) -> TabulaflowApp:
    return TabulaflowApp(
        llm_selection=selection,
        runtime_paths=runtime_paths or RuntimePaths.for_session("test-session"),
        project_dir=project_dir or Path.cwd(),
    )


def _app(
    preset: LLMPreset | None,
    *,
    runtime_paths: RuntimePaths | None = None,
    project_dir: Path | None = None,
) -> TabulaflowApp:
    return _app_for_selection(_selection(preset), runtime_paths=runtime_paths, project_dir=project_dir)


def _activate_selected(session: AppSession) -> ChatSession:
    assert session.selected_preset is not None
    session.activate_llm_preset(session.selected_preset)
    agent = session.active_chat_session
    assert agent is not None
    return agent


def test_reset_conversation_preserves_session_environment(tmp_path: Path) -> None:
    session = AppSession(
        llm_preset=_preset(),
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    agent = _activate_selected(session)
    initial_history = list(agent._message_history)
    output_store = agent.output_store
    agent.note_event("old conversation detail")

    session.reset_conversation()

    assert session.active_chat_session is agent
    assert len(agent._message_history) == len(initial_history)
    reset_part: Any = agent._message_history[0].parts[0]
    initial_part: Any = initial_history[0].parts[0]
    assert reset_part.content == initial_part.content
    assert agent.output_store is output_store
    assert agent._registry is session.registry


def test_text_selection_failure_is_contained(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(None)

    class BrokenSelectionScreen:
        selection_cleared = False

        def get_selected_text(self) -> str | None:
            raise IndexError("stale selection")

        def clear_selection(self) -> None:
            self.selection_cleared = True

    screen = BrokenSelectionScreen()
    monkeypatch.setattr(TabulaflowApp, "screen", property(lambda _app: screen))

    with caplog.at_level("DEBUG", logger=tui.__name__):
        app.on_text_selected(events.TextSelected())

    assert screen.selection_cleared is True
    assert "copying selected text failed" in caplog.text


def test_close_pane_removes_session_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = _app(None, runtime_paths=RuntimePaths.for_session("test-session"))
    pane_dir = app._runtime_paths.pane_dir
    pane_dir.mkdir(parents=True)
    (pane_dir / "card_test.data.json").write_text("{}")
    stopped: list[bool] = []

    class FakePane:
        def stop(self) -> None:
            stopped.append(True)

    app._pane = FakePane()  # type: ignore[assignment]

    app._close_pane(remove_artifacts=True)

    assert stopped == [True]
    assert app._pane is None
    assert not pane_dir.exists()


@pytest.mark.asyncio
async def test_ensure_session_creates_app_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.chdir(project_dir)

    preset = _preset(model="test:model", subagent_model="test:subagent")
    runtime_paths = RuntimePaths.for_session("test-session")
    app = _app(preset, runtime_paths=runtime_paths, project_dir=project_dir)

    session = object()
    captured: dict[str, Any] = {}

    async def fake_create_session(**kwargs: Any) -> object:
        captured["session_kwargs"] = kwargs
        return session

    monkeypatch.setattr(session_module.AppSession, "create", staticmethod(fake_create_session))
    monkeypatch.setattr(app, "_enable_explorer_button", lambda: None)

    result = await app._ensure_session()

    assert result is session
    assert captured["session_kwargs"] == {
        "llm_preset": preset,
        "runtime_paths": runtime_paths,
        "project_dir": project_dir,
    }


def test_bottom_status_shows_selected_model_before_agent_is_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset = _preset(
        model="anthropic:claude-opus-4-8",
        reasoning_effort="high",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
    )
    app = _app(preset, project_dir=tmp_path)
    session = AppSession(
        llm_preset=preset,
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    app._session = session
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)

    app._refresh_bottom_status()

    assert model_status.value.startswith("Opus 4.8 high · ")


def test_bottom_status_shows_startup_model_before_session_is_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _app(
        _preset(
            model="anthropic:claude-opus-4-8",
            reasoning_effort="high",
            subagent_model="anthropic:claude-sonnet-4-5-20250929",
        ),
        project_dir=tmp_path,
    )
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)

    app._refresh_bottom_status()

    assert model_status.value.startswith("Opus 4.8 high · ")


def test_bottom_status_shows_llm_off_before_session_when_no_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _app(None, project_dir=tmp_path)
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)

    app._refresh_bottom_status()

    assert model_status.value.startswith("LLM off · ")


def test_session_starts_with_unverified_llm_preset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    session = AppSession(
        llm_preset=_preset(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning_effort="medium",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
            subagent_reasoning_effort="medium",
        ),
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    assert session.active_chat_session is None
    assert session.selected_preset is not None
    assert session.selected_preset.main.model == "anthropic:claude-sonnet-4-5-20250929"
    assert session.registry.list_aliases() == []
    session.note_event("ignored without an LLM")

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        _activate_selected(session)
    assert session.active_chat_session is None


def test_initial_activation_requires_subagent_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = AppSession(
        llm_preset=_preset(
            model="test",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
        ),
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        _activate_selected(session)
    assert session.active_chat_session is None


def test_session_starts_without_llm_preset(tmp_path: Path) -> None:
    session = AppSession(
        llm_preset=None,
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    assert session.selected_preset is None
    assert session.active_chat_session is None


def test_llm_off_keeps_initialized_agent_dormant(tmp_path: Path) -> None:
    preset = _preset()
    session = AppSession(
        llm_preset=preset,
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    agent = _activate_selected(session)

    session.select_llm_preset(None)

    assert session.selected_preset is None
    assert session.active_chat_session is None
    session.select_llm_preset(preset)
    assert session.active_chat_session is agent


def test_unverified_session_can_select_and_then_build_valid_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = AppSession(
        llm_preset=_preset(
            model="anthropic:claude-sonnet-4-5-20250929",
            reasoning_effort="medium",
            subagent_model="anthropic:claude-haiku-4-5-20251001",
            subagent_reasoning_effort="medium",
        ),
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    session.select_llm_preset(_preset())
    session.activate_llm_preset(_preset())

    assert session.selected_preset == _preset()
    assert session.active_chat_session is not None


def test_selecting_unusable_preset_defers_error_until_agent_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = AppSession(
        llm_preset=_preset(),
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    old_agent = _activate_selected(session)
    old_model = old_agent.model

    selected_preset = _preset(
        model="anthropic:claude-sonnet-4-5-20250929",
        reasoning_effort="medium",
        subagent_model="anthropic:claude-haiku-4-5-20251001",
        subagent_reasoning_effort="medium",
    )
    session.select_llm_preset(selected_preset)
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        session.activate_llm_preset(selected_preset)
    assert session.selected_preset == selected_preset
    assert session.active_chat_session is None
    assert old_agent.model == old_model
    session.select_llm_preset(_preset())
    assert session.active_chat_session is old_agent


def test_switching_preset_preserves_live_chat_session_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    session = AppSession(
        llm_preset=_preset(
            model="openai-responses:gpt-5",
            reasoning_effort="medium",
            subagent_model="openai-responses:gpt-5-mini",
            subagent_reasoning_effort="low",
        ),
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    agent = _activate_selected(session)
    agent.note_event("remember this")
    message_history = agent._message_history
    output_store = agent.output_store

    selected_preset = _preset(
        model="openai-responses:gpt-5.4-mini",
        reasoning_effort="high",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning_effort="medium",
    )
    session.select_llm_preset(selected_preset)
    session.activate_llm_preset(selected_preset)

    assert session.active_chat_session is agent
    assert agent.resolve_api_keys()[0] == "sk-test123456789ab4x"
    assert agent._message_history is message_history
    assert agent.output_store is output_store


@pytest.mark.asyncio
async def test_startup_llm_activation_reports_session_then_agent_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = _preset(model="test:model")
    app = _app(preset)
    labels: list[str] = []

    async def fake_show(label: str) -> None:
        labels.append(label)

    class FakeSession:
        def activate_llm_preset(self, _preset: LLMPreset) -> tuple[None, None]:
            return None, None

    async def fake_ensure_session() -> object:
        return FakeSession()

    async def fake_finish(
        _selection: ResolvedLLMSelection,
        *,
        result: tuple[str | None, str | None] | Exception,
    ) -> None:
        assert result == (None, None)

    monkeypatch.setattr(app, "_show_initialization_spinner", fake_show)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(app, "_finish_llm_activation", fake_finish)

    await app._activate_llm_option(_selection(preset))

    assert labels == ["Initializing session...", "Initializing agent..."]


def test_llm_preset_success_message_places_api_keys_by_role() -> None:
    preset = _preset(
        model="anthropic:claude-opus-4-8",
        reasoning_effort="high",
        subagent_model="openai-responses:gpt-5.4-mini",
        subagent_reasoning_effort="medium",
    )

    shared = tui._llm_preset_success_message(
        preset,
        ("sk-shared123456789ABCD", "sk-shared123456789ABCD"),
    )
    assert shared.plain == "✓ LLM preset: Test · Opus 4.8 high → GPT 5.4 Mini medium [API key sk-***ABCD]"
    assert str(shared.style) == "dim"

    distinct = tui._llm_preset_success_message(
        preset,
        ("sk-main123456789AAAA", "sk-subagent123456BBBB"),
    )
    assert distinct.plain == (
        "✓ LLM preset: Test · Opus 4.8 high [API key sk-***AAAA] → GPT 5.4 Mini medium [API key sk-***BBBB]"
    )

    inferred = tui._llm_preset_success_message(
        preset,
        ("sk-shared123456789ABCD", "sk-shared123456789ABCD"),
        detected_api_key_env="ANTHROPIC_API_KEY",
    )
    assert inferred.plain == ("✓ ANTHROPIC_API_KEY detected (sk-***ABCD) · using Test. Change the preset in /config.")
    short_key = tui._llm_preset_success_message(
        preset,
        ("short", "short"),
        detected_api_key_env="ANTHROPIC_API_KEY",
    )
    assert short_key.plain == "✓ ANTHROPIC_API_KEY detected · using Test. Change the preset in /config."

    assert tui._masked_api_key("fw-api123456789WXYZ") == "fw-***WXYZ"
    assert tui._masked_api_key("short") is None


def test_llm_activation_error_normalization_is_actionable_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic_ai.exceptions import UserError

    preset = _preset(
        model="anthropic:claude-opus-4-8",
        subagent_model="openai-responses:gpt-5-mini",
    )

    assert (
        tui._normalize_llm_activation_error(
            UserError("Set the ANTHROPIC_API_KEY environment variable via AnthropicProvider."),
            preset,
        )
        == "ANTHROPIC_API_KEY is not set. Set it and restart the app, or choose another preset in /config."
    )
    openai_preset = _preset(
        model="openai-responses:gpt-5",
        subagent_model="openai-responses:gpt-5-mini",
    )
    openai_error = RuntimeError("Set the OPENAI_API_KEY environment variable.")
    openai_message = tui._normalize_llm_activation_error(openai_error, openai_preset)
    assert openai_message == (
        "OPENAI_API_KEY is not set. Set it and restart the app, or choose another preset in /config."
    )
    app = _app(openai_preset)
    app._llm_activation_error = openai_message
    assert app._llm_unavailable_message() == (
        "OPENAI_API_KEY is not set. Set it and restart the app, or choose another preset in /config. "
        "/connect and browsing remain available."
    )
    assert tui._normalize_llm_activation_error(UserError("Unknown model: invalid"), preset) == (
        "Unknown model: invalid. Update app_config.json or choose another preset in /config."
    )
    assert tui._normalize_llm_activation_error(ValueError("Unknown provider: invalid"), preset) == (
        "Unknown provider: invalid. Update app_config.json or choose another preset in /config."
    )
    assert tui._normalize_llm_activation_error(KeyError("GOOGLE_CLOUD_PROJECT"), preset) == (
        "GOOGLE_CLOUD_PROJECT is not set. Set it and restart the app, or choose another preset in /config."
    )

    api_key = "secret-api-key-1234"
    monkeypatch.setenv("VENDOR_API_KEY", api_key)
    normalized = tui._normalize_llm_activation_error(
        RuntimeError(f"first line\nsecond line leaked {api_key}"),
        preset,
    )
    assert normalized == (
        "Initialization failed: RuntimeError: first line second line leaked sec***1234. "
        "Choose another preset in /config."
    )
    assert api_key not in normalized

    bounded = tui._normalize_llm_activation_error(RuntimeError("x" * 500), preset)
    assert "… Choose another preset in /config." in bounded
    assert len(bounded) < 400


@pytest.mark.asyncio
async def test_session_failure_does_not_enter_llm_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    preset = _preset()
    app = _app(preset)
    error = OSError("workspace unavailable")
    reported: list[Exception] = []

    async def fake_show(_label: str) -> None:
        return None

    async def fake_ensure_session() -> object:
        raise error

    async def fake_report(caught: Exception) -> None:
        reported.append(caught)

    async def unexpected_finish(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("LLM activation should not finish after a session failure")

    monkeypatch.setattr(app, "_show_initialization_spinner", fake_show)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(app, "_report_session_initialization_failure", fake_report)
    monkeypatch.setattr(app, "_finish_llm_activation", unexpected_finish)

    await app._activate_llm_option(_selection(preset))

    assert reported == [error]
    assert app._llm_activation_error is None


@pytest.mark.asyncio
async def test_starting_llm_off_reports_available_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(None)
    session_started = asyncio.Event()
    release_session = asyncio.Event()

    async def fake_ensure_session() -> object:
        session_started.set()
        await release_session.wait()
        return _InactiveSession()

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        await asyncio.wait_for(session_started.wait(), timeout=2)
        await pilot.pause()
        assert app.query_one(SpinnerWidget)._label == "Initializing session..."

        release_session.set()
        for _ in range(3):
            await pilot.pause()
        assert len(app.query(SpinnerWidget)) == 0
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == ["✓ LLM off · /connect and the data explorer remain available."]
        app._llm_activation_error = "old failure"
        app._llm_activation_in_progress = True

        app._start_llm_activation(_selection(None))
        for _ in range(2):
            await pilot.pause()

        assert not app._llm_activation_in_progress
        assert app._llm_activation_error is None
        assert not app.query_one("#input-bar", Input).disabled
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == [
            "✓ LLM off · /connect and the data explorer remain available.",
            "✓ LLM off · /connect and the data explorer remain available.",
        ]


@pytest.mark.asyncio
async def test_startup_paints_banner_before_starting_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(None)
    started: list[bool] = []

    def fake_start(_selection: ResolvedLLMSelection) -> None:
        banner = app.query_one(BannerWidget)
        started.append(banner.query_one(".banner-art", Static).is_mounted)

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_start_llm_activation", fake_start)

    async with app.run_test() as pilot:
        await pilot.pause()

        chat_log = app.query_one("#chat-log", VerticalScroll)
        assert [type(child) for child in chat_log.children[:2]] == [BannerWidget, SpinnerWidget]
        assert started == [True]


@pytest.mark.asyncio
async def test_unconfigured_without_detected_key_explains_why_llm_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app_for_selection(_selection(None, inferred=True))

    async def fake_ensure_session() -> object:
        return _InactiveSession()

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()

        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == ["✓ LLM off · no supported API key detected. Choose a preset in /config."]


@pytest.mark.asyncio
async def test_inferred_startup_reports_masked_api_key_in_chat_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = _preset(
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning_effort="medium",
    )
    app = _app_for_selection(_selection(preset, inferred=True, detected_api_key_env="OPENAI_API_KEY"))

    class FakeSession:
        def activate_llm_preset(self, selected: LLMPreset) -> tuple[str | None, str | None]:
            assert selected == preset
            return "sk-main123456789E0QA", "sk-main123456789E0QA"

    async def fake_ensure_session() -> object:
        return FakeSession()

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == ["✓ OPENAI_API_KEY detected (sk-***E0QA) · using Test. Change the preset in /config."]
        assert not app._llm_activation_in_progress
        assert not app.query_one("#input-bar", Input).disabled


@pytest.mark.asyncio
async def test_failed_startup_activation_reports_error_and_unblocks_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = _preset(model="anthropic:claude-opus-4-8", reasoning_effort="high")
    app = _app(preset)

    class FakeSession:
        def activate_llm_preset(self, _selected: LLMPreset) -> tuple[str | None, str | None]:
            raise RuntimeError("missing credential")

    async def fake_ensure_session() -> object:
        return FakeSession()

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == [
            "LLM unavailable: Initialization failed: RuntimeError: missing credential. "
            "Choose another preset in /config. /connect and browsing remain available."
        ]
        assert app._llm_unavailable_message() == (
            "Initialization failed: RuntimeError: missing credential. "
            "Choose another preset in /config. /connect and browsing remain available."
        )
        assert not app._llm_activation_in_progress
        assert not app.query_one("#input-bar", Input).disabled


@pytest.mark.asyncio
async def test_llm_activation_preserves_blocked_submissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(None)

    async def fake_ensure_session() -> object:
        return _InactiveSession()

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        input_bar = app.query_one("#input-bar", HistoryInput)
        initial_history = list(input_bar._history)
        app._llm_activation_in_progress = True

        input_bar.value = "show recent orders"
        await pilot.press("enter")
        await pilot.pause()

        assert input_bar.value == "show recent orders"
        assert input_bar._history == initial_history
        assert len(app.query(UserMessage)) == 0

        input_bar.value = "/help"
        await pilot.press("enter")
        await pilot.pause()

        assert input_bar.value == "/help"
        assert input_bar._history == initial_history
        assert len(app.query(UserMessage)) == 0


@pytest.mark.asyncio
async def test_submission_worker_blocks_input_until_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    command_started = asyncio.Event()
    release_command = asyncio.Event()

    async def fake_ensure_session() -> object:
        return _InactiveSession()

    async def fake_handle_command(_text: str, _session: object) -> CommandResult:
        command_started.set()
        await release_command.wait()
        return CommandResult()

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(tui, "handle_command", fake_handle_command)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        input_bar = app.query_one("#input-bar", HistoryInput)
        input_bar.value = "/help"
        await pilot.press("enter")
        await asyncio.wait_for(command_started.wait(), timeout=2)

        assert app._submission_worker is not None
        input_bar.value = "next question"
        await pilot.press("enter")
        await pilot.pause()

        assert input_bar.value == "next question"
        assert len(app.query(UserMessage)) == 1

        release_command.set()
        for _ in range(2):
            await pilot.pause()

        assert app._submission_worker is None


@pytest.mark.asyncio
async def test_submission_worker_covers_and_can_cancel_session_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    preflight_started = asyncio.Event()
    release_preflight = asyncio.Event()

    async def initial_session() -> object:
        return _InactiveSession()

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", initial_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()

        async def blocking_session() -> object:
            preflight_started.set()
            await release_preflight.wait()
            return _InactiveSession()

        monkeypatch.setattr(app, "_ensure_session", blocking_session)
        input_bar = app.query_one("#input-bar", HistoryInput)
        input_bar.value = "show recent orders"
        await pilot.press("enter")
        await asyncio.wait_for(preflight_started.wait(), timeout=2)

        assert app._submission_worker is not None
        input_bar.value = "next question"
        await pilot.press("enter")
        await pilot.pause()
        assert input_bar.value == "next question"
        assert len(app.query(UserMessage)) == 1

        input_bar.clear()
        await pilot.press("ctrl+c")
        for _ in range(2):
            await pilot.pause()

        assert app._submission_worker is None
        assert input_bar.value == "show recent orders"
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages[-1] == "Interrupted"


@pytest.mark.asyncio
async def test_config_selection_persists_and_starts_one_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    session = _InactiveSession()
    updates: list[dict[str, object]] = []
    activations: list[ResolvedLLMSelection] = []

    async def fake_ensure_session() -> object:
        app._session = session  # type: ignore[assignment]
        return session

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(tui, "update_app_config", lambda **prefs: updates.append(prefs))

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        monkeypatch.setattr(app, "_start_llm_activation", activations.append)
        preset = _preset(label="Selected")

        selection = ResolvedLLMSelection("Selected", preset)
        app._on_config_closed(selection)
        await pilot.pause()

        assert session.selected_preset == preset
        assert updates == [{"llm_preset": "Selected"}]
        assert activations == [selection]


@pytest.mark.asyncio
async def test_closing_config_restores_input_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)

    async def fake_ensure_session() -> object:
        return _InactiveSession()

    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        explorer_button = app.query_one("#open-explorer-btn", Button)
        explorer_button.disabled = False
        explorer_button.focus()
        await pilot.pause()
        assert explorer_button.has_focus

        app._on_config_closed(None)
        await pilot.pause()

        assert app.query_one("#input-bar", Input).has_focus


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


@pytest.mark.asyncio
async def test_run_tui_restores_terminal_modes_after_normal_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = _FakeStdout()
    _FakeRunTuiApp.error = None
    _FakeRunTuiApp.run_mouse = None
    _FakeRunTuiApp.pane_close_args = []

    monkeypatch.setattr(sys, "__stdout__", stdout)
    monkeypatch.setattr(tui, "TabulaflowApp", _FakeRunTuiApp)

    await tui.run_tui(_selection(None))

    assert _FakeRunTuiApp.run_mouse is True
    assert _FakeRunTuiApp.pane_close_args == [True]
    assert stdout.value == tui._TERMINAL_MODE_RESTORE_SEQUENCE
    assert stdout.flushed is True


@pytest.mark.asyncio
async def test_run_tui_restores_terminal_modes_after_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = _FakeStdout()
    error = RuntimeError("boom")
    _FakeRunTuiApp.error = error
    _FakeRunTuiApp.run_mouse = None
    _FakeRunTuiApp.pane_close_args = []

    monkeypatch.setattr(sys, "__stdout__", stdout)
    monkeypatch.setattr(tui, "TabulaflowApp", _FakeRunTuiApp)

    with pytest.raises(RuntimeError, match="boom"):
        await tui.run_tui(_selection(None))

    assert _FakeRunTuiApp.run_mouse is True
    assert _FakeRunTuiApp.pane_close_args == [True]
    assert stdout.value == tui._TERMINAL_MODE_RESTORE_SEQUENCE
    assert stdout.flushed is True
