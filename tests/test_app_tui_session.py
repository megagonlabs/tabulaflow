from __future__ import annotations

import asyncio
from pathlib import Path
import threading
from typing import TYPE_CHECKING, Any

import pytest
from textual.widgets import Input

from tabulaflow.app import session as session_module
from tabulaflow.app import tui
from tabulaflow.app.config import LLMRoleConfig, LLMPreset, ReasoningEffort
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.session import SessionState
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.app.widgets import SpinnerWidget, SystemMessage

if TYPE_CHECKING:
    from tabulaflow.chat import ChatAgent


class _StatusCapture:
    def __init__(self) -> None:
        self.value = ""

    def update(self, value: object) -> None:
        self.value = str(value)


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


def _activate_selected(session: SessionState) -> ChatAgent:
    assert session.llm_preset is not None
    session.activate_llm_preset(session.llm_preset)
    agent = session.active_chat_agent
    assert agent is not None
    return agent


@pytest.mark.asyncio
async def test_ensure_session_passes_session_paths_by_keyword(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.chdir(project_dir)

    preset = _preset(model="test:model", subagent_model="test:subagent")
    app = TabulaflowApp(
        llm_preset=preset,
    )
    runtime_paths = RuntimePaths.for_session("test-session")
    app._runtime_paths = runtime_paths

    workspace = object()
    session = object()
    captured: dict[str, Any] = {}

    async def fake_create_workspace_connector(workspace_db_path: Path) -> object:
        captured["workspace_db_path"] = workspace_db_path
        return workspace

    def fake_session_state(**kwargs: Any) -> object:
        captured["session_kwargs"] = kwargs
        return session

    async def fake_autoconnect_sample(_session: object) -> None:
        captured["autoconnect_session"] = _session

    monkeypatch.setattr(session_module, "create_workspace_connector", fake_create_workspace_connector)
    monkeypatch.setattr(tui, "_warm_session_imports", lambda: None)
    monkeypatch.setattr(tui, "SessionState", fake_session_state)
    monkeypatch.setattr(app, "_maybe_autoconnect_sample", fake_autoconnect_sample)
    monkeypatch.setattr(app, "_enable_explorer_button", lambda: None)

    result = await app._ensure_session()

    assert result is session
    assert captured["workspace_db_path"] == runtime_paths.workspace_db_path
    assert captured["autoconnect_session"] is session
    assert captured["session_kwargs"] == {
        "llm_preset": preset,
        "trajectories_dir": runtime_paths.trajectories_dir,
        "data_dir": runtime_paths.data_dir,
        "workspace": workspace,
        "project_dir": project_dir,
        "scratch_dir": runtime_paths.scratch_dir,
    }


def test_bottom_status_shows_selected_model_before_agent_is_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset = _preset(
        model="anthropic:claude-opus-4-8",
        reasoning_effort="high",
        subagent_model="anthropic:claude-sonnet-4-5-20250929",
    )
    app = TabulaflowApp(llm_preset=preset)
    app._project_dir = tmp_path
    session = SessionState(
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
    app = TabulaflowApp(
        llm_preset=_preset(
            model="anthropic:claude-opus-4-8",
            reasoning_effort="high",
            subagent_model="anthropic:claude-sonnet-4-5-20250929",
        )
    )
    app._project_dir = tmp_path
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
    app = TabulaflowApp(llm_preset=None)
    app._project_dir = tmp_path
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)

    app._refresh_bottom_status()

    assert model_status.value.startswith("LLM off · ")


def test_session_starts_with_unverified_llm_preset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    session = SessionState(
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

    assert session.active_chat_agent is None
    assert session.llm_preset is not None
    assert session.llm_preset.main.model == "anthropic:claude-sonnet-4-5-20250929"
    assert session.registry.list_aliases() == []
    session.note_event("ignored without an LLM")

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        _activate_selected(session)
    assert session.active_chat_agent is None


def test_initial_activation_requires_subagent_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = SessionState(
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
    assert session.active_chat_agent is None


def test_session_starts_without_llm_preset(tmp_path: Path) -> None:
    session = SessionState(
        llm_preset=None,
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )

    assert session.llm_preset is None
    assert session.active_chat_agent is None


def test_llm_off_keeps_initialized_agent_dormant(tmp_path: Path) -> None:
    preset = _preset()
    session = SessionState(
        llm_preset=preset,
        trajectories_dir=tmp_path / "trajectories",
        data_dir=tmp_path / "data",
        workspace=None,
    )
    agent = _activate_selected(session)

    session.set_llm_preset(None)

    assert session.llm_preset is None
    assert session.active_chat_agent is None
    session.set_llm_preset(preset)
    assert session.active_chat_agent is agent


def test_unverified_session_can_select_and_then_build_valid_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = SessionState(
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

    session.set_llm_preset(_preset())

    assert session.active_chat_agent is None
    assert session.llm_preset == _preset()

    _activate_selected(session)
    assert session.active_chat_agent is not None


def test_selecting_unusable_preset_defers_error_until_agent_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    session = SessionState(
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
    session.set_llm_preset(selected_preset)

    assert session.active_chat_agent is None
    assert session.llm_preset == selected_preset

    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        _activate_selected(session)
    assert session.active_chat_agent is None
    assert old_agent.model == old_model
    session.set_llm_preset(_preset())
    assert session.active_chat_agent is old_agent


def test_switching_preset_preserves_live_chat_agent_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    session = SessionState(
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
    query_history = agent.query_history

    session.set_llm_preset(
        _preset(
            model="openai-responses:gpt-5.4-mini",
            reasoning_effort="high",
            subagent_model="openai-responses:gpt-5-mini",
            subagent_reasoning_effort="medium",
        )
    )

    assert session.active_chat_agent is None
    _activate_selected(session)
    assert session.active_chat_agent is agent
    assert agent.resolve_api_keys()[0] == "sk-test123456789ab4x"
    assert agent._message_history is message_history
    assert agent.query_history is query_history


@pytest.mark.asyncio
async def test_startup_llm_activation_reports_session_then_agent_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = _preset(model="test:model")
    app = TabulaflowApp(llm_preset=preset)
    labels: list[str] = []

    async def fake_show(label: str) -> None:
        labels.append(label)

    async def fake_ensure_session() -> object:
        return object()

    async def fake_finish(
        _request_id: int,
        _preset: LLMPreset,
        *,
        result: tuple[str | None, str | None] | Exception,
    ) -> None:
        assert result == (None, None)

    monkeypatch.setattr(app, "_show_initialization_spinner", fake_show)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(app, "_initialize_llm_runtime", lambda _session, _preset: (None, None))
    monkeypatch.setattr(app, "_finish_llm_activation", fake_finish)

    app._llm_activation_request_id = 1
    await app._activate_llm_option(1, preset)

    assert labels == ["Initializing session...", "Initializing agent..."]


@pytest.mark.asyncio
async def test_llm_activation_only_publishes_latest_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    first = _preset(label="First", model="test:first")
    latest = _preset(label="Latest", model="test:latest")
    app = TabulaflowApp(llm_preset=first)
    started = threading.Event()
    release = threading.Event()
    initialized: list[LLMPreset] = []
    finished: list[tuple[LLMPreset, tuple[str | None, str | None] | Exception]] = []

    async def fake_show(_label: str) -> None:
        return None

    async def fake_ensure_session() -> object:
        return object()

    def fake_initialize(_session: object, preset: LLMPreset) -> tuple[str | None, str | None]:
        initialized.append(preset)
        if preset == first:
            started.set()
            assert release.wait(timeout=2)
        return f"sk-test123456789{preset.label}", None

    async def fake_finish(
        _request_id: int,
        preset: LLMPreset,
        *,
        result: tuple[str | None, str | None] | Exception,
    ) -> None:
        finished.append((preset, result))

    monkeypatch.setattr(app, "_show_initialization_spinner", fake_show)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(app, "_initialize_llm_runtime", fake_initialize)
    monkeypatch.setattr(app, "_finish_llm_activation", fake_finish)

    app._llm_activation_request_id = 1
    first_task = asyncio.create_task(app._activate_llm_option(1, first))
    assert await asyncio.to_thread(started.wait, 2)
    app._llm_activation_request_id = 2
    latest_task = asyncio.create_task(app._activate_llm_option(2, latest))
    release.set()
    await asyncio.gather(first_task, latest_task)

    assert initialized == [first, latest]
    assert finished == [(latest, ("sk-test123456789Latest", None))]


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
    assert shared.plain == "✓ LLM preset: Opus 4.8 high → GPT 5.4 Mini medium [API key sk-***ABCD]"
    assert str(shared.style) == "dim"

    distinct = tui._llm_preset_success_message(
        preset,
        ("sk-main123456789AAAA", "sk-subagent123456BBBB"),
    )
    assert distinct.plain == (
        "✓ LLM preset: Opus 4.8 high [API key sk-***AAAA] → GPT 5.4 Mini medium [API key sk-***BBBB]"
    )

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
    app = TabulaflowApp(llm_preset=openai_preset)
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
    app = TabulaflowApp(llm_preset=preset)
    error = OSError("workspace unavailable")
    reported: list[Exception] = []

    async def fake_show(_label: str) -> None:
        return None

    async def fake_ensure_session() -> object:
        raise error

    async def fake_report(_request_id: int, caught: Exception) -> None:
        reported.append(caught)

    async def unexpected_finish(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("LLM activation should not finish after a session failure")

    monkeypatch.setattr(app, "_show_initialization_spinner", fake_show)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(app, "_report_session_initialization_failure", fake_report)
    monkeypatch.setattr(app, "_finish_llm_activation", unexpected_finish)

    app._llm_activation_request_id = 1
    await app._activate_llm_option(1, preset)

    assert reported == [error]
    assert app._llm_activation_error is None


@pytest.mark.asyncio
async def test_selecting_llm_off_cancels_activation_and_reports_available_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = TabulaflowApp(llm_preset=None)
    session_started = asyncio.Event()
    release_session = asyncio.Event()

    async def fake_ensure_session() -> object:
        session_started.set()
        await release_session.wait()
        return object()

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
        assert messages == ["✓ LLM off. Connect a data source with /connect and inspect it in the data explorer."]
        request_id = app._llm_activation_request_id
        app._llm_activation_error = "old failure"
        app.query_one("#input-bar", Input).disabled = True

        app._on_llm_option_selected(None)
        for _ in range(2):
            await pilot.pause()

        assert app._llm_activation_request_id == request_id + 1
        assert app._llm_activation_error is None
        assert not app.query_one("#input-bar", Input).disabled
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == [
            "✓ LLM off. Connect a data source with /connect and inspect it in the data explorer.",
            "✓ LLM off. Connect a data source with /connect and inspect it in the data explorer.",
        ]


@pytest.mark.asyncio
async def test_startup_activation_reports_masked_api_key_in_chat_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = _preset(
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        subagent_model="openai-responses:gpt-5-mini",
        subagent_reasoning_effort="medium",
    )
    app = TabulaflowApp(llm_preset=preset)

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
        assert messages == ["✓ LLM preset: GPT 5 medium → GPT 5 Mini medium [API key sk-***E0QA]"]
        assert not app.query_one("#input-bar", Input).disabled


@pytest.mark.asyncio
async def test_failed_startup_activation_reports_error_and_unblocks_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = _preset(model="anthropic:claude-opus-4-8", reasoning_effort="high")
    app = TabulaflowApp(llm_preset=preset)

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
        assert not app.query_one("#input-bar", Input).disabled
