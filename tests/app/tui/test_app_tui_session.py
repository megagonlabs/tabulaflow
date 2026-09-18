from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic_ai.messages import BinaryContent
from pydantic_ai.exceptions import UserError
from rich.console import Console
from rich.text import Text
from textual import events
from textual.containers import VerticalScroll
from textual.widgets import Button, Static

from tabulaflow.app import session as session_module
from tabulaflow.agents.chat import ChatResult
from tabulaflow.agents.llm import ReasoningLevel
from tabulaflow.app.tui import app as tui
from tabulaflow.app.tui.commands import (
    CommandResult,
    HuggingFaceSubsetSelection,
)
from tabulaflow.app.config import LLM_OFF, LLMRoleConfig, LLMConfig, ResolvedLLMConfig
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.session import AppSession
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.app.tui.widgets.chat import BannerWidget, SpinnerWidget, SystemMessage, UserMessage
from tabulaflow.app.tui.widgets.chat_log import ChatLog
from tabulaflow.app.tui.widgets.choice import InlineChoiceSelector
from tabulaflow.app.tui.widgets.input import HistoryInput
from tabulaflow.app.tui.widgets.result import AgentResultWidget
from tabulaflow.app.tui.widgets.suggestions import InputSuggestionMenu


class _StatusCapture:
    def __init__(self) -> None:
        self.value = ""

    def update(self, value: object) -> None:
        self.value = str(value)


class _InactiveSession:
    selected_llm_config: LLMConfig | None = None

    def select_llm_config(self, config: LLMConfig | None) -> None:
        self.selected_llm_config = config

    def activate_llm_config(self, config: LLMConfig | None) -> tuple[None, None]:
        return None, None


def _llm_config(
    *,
    label: str = "Test",
    model: str = "test",
    reasoning: ReasoningLevel = "low",
    subagent_model: str = "test",
    subagent_reasoning: ReasoningLevel = "medium",
) -> LLMConfig:
    return LLMConfig(
        main=LLMRoleConfig(model=model, reasoning=reasoning),
        subagent=LLMRoleConfig(model=subagent_model, reasoning=subagent_reasoning),
    )


def _selection(
    config: LLMConfig | None,
    *,
    inferred: bool = False,
    detected_api_key_env: str | None = None,
) -> ResolvedLLMConfig:
    selection = None if inferred else (config if config is not None else LLM_OFF)
    return ResolvedLLMConfig(selection, config, detected_api_key_env)


def _app_for_selection(
    selection: ResolvedLLMConfig,
    *,
    runtime_paths: RuntimePaths | None = None,
    project_dir: Path | None = None,
    llm_service_tier: str = "default",
    enable_schema_cache: bool = False,
) -> TabulaflowApp:
    from tabulaflow.agents.llm import ServiceTier

    return TabulaflowApp(
        llm_config=selection,
        runtime_paths=runtime_paths or RuntimePaths.for_session("test-session"),
        project_dir=project_dir or Path.cwd(),
        llm_service_tier=cast(ServiceTier, llm_service_tier),
        enable_schema_cache=enable_schema_cache,
    )


def _app(
    config: LLMConfig | None,
    *,
    runtime_paths: RuntimePaths | None = None,
    project_dir: Path | None = None,
) -> TabulaflowApp:
    return _app_for_selection(_selection(config), runtime_paths=runtime_paths, project_dir=project_dir)


def _stub_app_startup(app: TabulaflowApp, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)


def _session(*, llm_config: LLMConfig | None, tmp_path: Path) -> AppSession:
    return AppSession(
        llm_config=llm_config,
        runtime_paths=RuntimePaths.for_session("test-session", home_dir=tmp_path),
        workspace=None,
    )


def test_crash_console_disables_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Console, "_detect_color_system", lambda _console: "standard")

    assert _app(None).error_console.color_system is None


async def test_escape_returns_to_previously_focused_result(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    _stub_app_startup(app, monkeypatch)

    async with app.run_test(size=(100, 36)) as pilot:
        chat_log = app.query_one("#chat-log", ChatLog)
        first = AgentResultWidget(ChatResult(text="first"), [])
        second = AgentResultWidget(ChatResult(text="second"), [])
        await chat_log.mount(first, second)

        input_bar = app.query_one("#input-bar", HistoryInput)
        input_bar.focus()
        app._last_focused_result = None
        await pilot.press("escape")
        assert second.has_focus

        await pilot.press("escape")
        assert input_bar.has_focus

        first.focus()
        await pilot.pause()
        await pilot.press("escape")
        assert input_bar.has_focus

        await pilot.press("/")
        await pilot.pause()
        await pilot.press("escape")
        assert input_bar.has_focus
        assert not app.query_one(InputSuggestionMenu).suggestions

        await pilot.press("escape")
        assert first.has_focus


async def test_clear_resets_tui_and_output_pane(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    _stub_app_startup(app, monkeypatch)

    class FakePane:
        cleared = False

        def clear(self) -> None:
            self.cleared = True

    pane = FakePane()
    app._pane = pane  # type: ignore[assignment]

    async with app.run_test(size=(100, 36)) as pilot:
        await pilot.pause()
        chat_log = app.query_one(ChatLog)
        await chat_log.mount(SystemMessage("old conversation"))

        await app._show_command_result(
            CommandResult(action="clear"),
            cast(AppSession, object()),
            chat_log,
        )

        assert pane.cleared
        assert len(app.query(SystemMessage)) == 0
        assert len(app.query(BannerWidget)) == 1


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


async def test_huggingface_subset_selection_connects_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_start_llm_activation", lambda _selection: None)
    session = object()
    app._session = session  # type: ignore[assignment]
    selected: list[str] = []

    async def complete_selection(
        _selection: HuggingFaceSubsetSelection,
        subset: str,
        _session: AppSession,
    ) -> CommandResult:
        selected.append(subset)
        return CommandResult(output=Text("✓ Connected to glue"))

    monkeypatch.setattr(tui, "complete_hf_subset_selection", complete_selection)
    request = HuggingFaceSubsetSelection(
        alias="glue",
        dataset_id="nyu-mll/glue",
        subsets=("cola", "mnli", "mrpc"),
    )

    async with app.run_test(size=(100, 36)) as pilot:
        await pilot.pause()
        chat_log = app.query_one(ChatLog)
        await app._show_command_result(
            CommandResult(action=request),
            session,  # type: ignore[arg-type]
            chat_log,
        )

        selector = app.query_one(InlineChoiceSelector)
        assert selector.has_focus
        assert app.query_one("#input-bar", HistoryInput).disabled

        await pilot.press("m", "r", "enter")
        await pilot.pause()

        assert selected == ["mrpc"]
        assert len(app.query(InlineChoiceSelector)) == 0
        assert app.query_one("#input-bar", HistoryInput).has_focus
        assert "✓ Connected to glue" in [cast(Text, message.render()).plain for message in app.query(SystemMessage)]


async def test_explorer_control_stays_aligned_with_bottom_of_multiline_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(None)
    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_start_llm_activation", lambda _selection: None)

    async with app.run_test(size=(100, 36)) as pilot:
        input_bar = app.query_one("#input-bar", HistoryInput)
        input_row = app.query_one("#input-row")
        assert input_row.size.height == input_bar.size.height == 1

        input_bar.value = "x" * 500
        await pilot.pause()

        explorer_button = app.query_one("#open-explorer-btn", Button)
        assert input_bar.size.height == 5
        assert input_row.size.height == input_bar.size.height
        assert explorer_button.region.bottom == input_bar.region.bottom


async def test_huggingface_subset_connection_uses_submission_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_start_llm_activation", lambda _selection: None)
    session = object()
    app._session = session  # type: ignore[assignment]
    started = asyncio.Event()
    cancelled = asyncio.Event()
    opened_explorer: list[bool] = []

    async def complete_selection(
        _selection: HuggingFaceSubsetSelection,
        _subset: str,
        _session: AppSession,
    ) -> CommandResult:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise
        raise AssertionError("unreachable")

    monkeypatch.setattr(tui, "complete_hf_subset_selection", complete_selection)
    monkeypatch.setattr(app, "action_open_data_explorer", lambda: opened_explorer.append(True))
    request = HuggingFaceSubsetSelection(
        alias="glue",
        dataset_id="nyu-mll/glue",
        subsets=("cola", "mnli", "mrpc"),
    )

    async with app.run_test(size=(100, 36)) as pilot:
        await pilot.pause()
        await app._show_command_result(
            CommandResult(action=request),
            session,  # type: ignore[arg-type]
            app.query_one(ChatLog),
        )
        await pilot.press("enter")
        await started.wait()

        input_bar = app.query_one("#input-bar", HistoryInput)
        assert app._submission_worker is not None
        assert input_bar.has_focus
        assert not input_bar.disabled

        await pilot.press("n", "e", "x", "t")
        await pilot.press("ctrl+o")
        await pilot.pause()

        assert input_bar.value == "next"
        assert opened_explorer == [True]

        await pilot.press("ctrl+c")
        await cancelled.wait()
        await pilot.pause()

        assert app._submission_worker is None
        assert input_bar.value == "next"
        assert "Interrupted" in [cast(Text, message.render()).plain for message in app.query(SystemMessage)]


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


async def test_agent_failure_is_logged_with_traceback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = _app(None)
    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_start_llm_activation", lambda _selection: None)

    class FailingSession:
        last_usage = None

        async def run_stream(self, _question: object) -> Any:
            raise RuntimeError("agent failure detail")
            yield

    async with app.run_test() as pilot:
        await pilot.pause()
        with caplog.at_level("ERROR", logger=tui.__name__):
            await app._run_agent("question", FailingSession(), app.query_one(ChatLog), "question")  # type: ignore[arg-type]
        messages = [str(message.render()) for message in app.query(SystemMessage)]

    assert "agent turn failed (pane_turn_id=None)" in caplog.text
    assert "RuntimeError: agent failure detail" in caplog.text
    assert messages == ["Agent turn failed: agent failure detail."]


async def test_agent_failure_without_message_shows_exception_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(None)
    monkeypatch.setattr(app, "_setup_logging", lambda: None)
    monkeypatch.setattr(app, "_ensure_pane", lambda: None)
    monkeypatch.setattr(app, "_start_llm_activation", lambda _selection: None)

    class FailingSession:
        last_usage = None

        async def run_stream(self, _question: object) -> Any:
            raise TimeoutError
            yield

    async with app.run_test() as pilot:
        await pilot.pause()
        await app._run_agent("question", FailingSession(), app.query_one(ChatLog), "question")  # type: ignore[arg-type]
        messages = [str(message.render()) for message in app.query(SystemMessage)]

    assert messages == ["Agent turn failed: TimeoutError."]


async def test_ensure_session_creates_app_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.chdir(project_dir)

    config = _llm_config(model="test:model", subagent_model="test:subagent")
    runtime_paths = RuntimePaths.for_session("test-session")
    app = _app_for_selection(
        _selection(config),
        runtime_paths=runtime_paths,
        project_dir=project_dir,
        enable_schema_cache=True,
    )

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
        "llm_config": config,
        "runtime_paths": runtime_paths,
        "project_dir": project_dir,
        "llm_service_tier": "default",
        "enable_schema_cache": True,
    }


@pytest.mark.parametrize(
    ("llm_enabled", "session_ready", "expected"),
    [
        (True, True, "claude-opus-4-8 · high · "),
        (True, False, "claude-opus-4-8 · high · "),
        (False, False, "LLM off · "),
    ],
)
def test_bottom_status_uses_selected_startup_profile(
    llm_enabled: bool,
    session_ready: bool,
    expected: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = (
        _llm_config(
            model="anthropic:claude-opus-4-8",
            reasoning="high",
            subagent_model="anthropic:claude-sonnet-4-5-20250929",
        )
        if llm_enabled
        else None
    )
    app = _app(config, project_dir=tmp_path)
    if session_ready:
        app._session = _session(llm_config=config, tmp_path=tmp_path)
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)
    app._refresh_bottom_status()

    assert model_status.value.startswith(expected)


def test_bottom_status_discloses_priority_llm_service_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _llm_config(model="openai:gpt-5.6-sol")
    app = _app_for_selection(_selection(config), project_dir=tmp_path, llm_service_tier="priority")
    model_status = _StatusCapture()
    url_status = _StatusCapture()

    def fake_query_one(selector: str, _type: object) -> _StatusCapture:
        return model_status if selector == "#bottom-status-model" else url_status

    monkeypatch.setattr(app, "query_one", fake_query_one)
    app._refresh_bottom_status()

    assert model_status.value.startswith("gpt-5.6-sol · low · Priority · ")


async def test_startup_llm_activation_reports_session_then_agent_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _llm_config(model="test:model")
    app = _app(config)
    labels: list[str] = []

    async def fake_show(label: str) -> None:
        labels.append(label)

    class FakeSession:
        def activate_llm_config(self, _llm_config: LLMConfig) -> tuple[None, None]:
            return None, None

    async def fake_ensure_session() -> object:
        return FakeSession()

    async def fake_finish(
        _selection: ResolvedLLMConfig,
        *,
        result: tuple[str | None, str | None] | Exception,
    ) -> None:
        assert result == (None, None)

    monkeypatch.setattr(app, "_show_initialization_spinner", fake_show)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(app, "_finish_llm_activation", fake_finish)

    await app._activate_llm_option(_selection(config))

    assert labels == ["Initializing session...", "Initializing agent..."]


@pytest.mark.parametrize(
    ("api_keys", "detected_env", "expected"),
    [
        (
            ("sk-shared123456789ABCD", "sk-shared123456789ABCD"),
            None,
            "✓ Main: claude-opus-4-8 · high · Subagent: gpt-5.4-mini · medium [API key sk-***ABCD]",
        ),
        (
            ("sk-main123456789AAAA", "sk-subagent123456BBBB"),
            None,
            "✓ Main: claude-opus-4-8 · high [API key sk-***AAAA] · Subagent: gpt-5.4-mini · medium [API key sk-***BBBB]",
        ),
        (
            ("sk-shared123456789ABCD", "sk-shared123456789ABCD"),
            "ANTHROPIC_API_KEY",
            "✓ ANTHROPIC_API_KEY detected (sk-***ABCD) · using claude-opus-4-8. Change models in /config.",
        ),
        (
            ("short", "short"),
            "ANTHROPIC_API_KEY",
            "✓ ANTHROPIC_API_KEY detected · using claude-opus-4-8. Change models in /config.",
        ),
    ],
)
def test_llm_config_success_message(
    api_keys: tuple[str, str],
    detected_env: str | None,
    expected: str,
) -> None:
    config = _llm_config(
        model="anthropic:claude-opus-4-8",
        reasoning="high",
        subagent_model="openai:gpt-5.4-mini",
    )

    message = tui._llm_config_success_message(config, api_keys, detected_api_key_env=detected_env)

    assert message.plain == expected
    assert str(message.style) == "dim"


@pytest.mark.parametrize(
    ("api_key", "expected"),
    [("fw-api123456789WXYZ", "fw-***WXYZ"), ("short", None)],
)
def test_masked_api_key(api_key: str, expected: str | None) -> None:
    assert tui._masked_api_key(api_key) == expected


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            UserError("Set the ANTHROPIC_API_KEY environment variable via AnthropicProvider."),
            "ANTHROPIC_API_KEY is not set. Set it and restart TabulaFlow, or choose another model in /config.",
        ),
        (
            RuntimeError("Set the OPENAI_API_KEY environment variable."),
            "OPENAI_API_KEY is not set. Set it and restart TabulaFlow, or choose another model in /config.",
        ),
        (
            UserError("Set the `ZAI_API_KEY` environment variable or pass it via `ZaiProvider(api_key=...)`."),
            "ZAI_API_KEY is not set. Set it and restart TabulaFlow, or choose another model in /config.",
        ),
        (
            UserError("Unknown model: invalid"),
            "Unknown model: invalid. Choose another model in /config.",
        ),
        (
            ValueError("Unknown provider: invalid"),
            "Unknown provider: invalid. Choose another model in /config.",
        ),
        (
            KeyError("GOOGLE_CLOUD_PROJECT"),
            "GOOGLE_CLOUD_PROJECT is not set. Set it and restart TabulaFlow, or choose another model in /config.",
        ),
    ],
)
def test_llm_activation_error_is_actionable(error: Exception, expected: str) -> None:
    assert tui._normalize_llm_activation_error(error) == expected


def test_llm_activation_error_is_redacted_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = "secret-api-key-1234"
    monkeypatch.setenv("VENDOR_API_KEY", api_key)

    normalized = tui._normalize_llm_activation_error(
        RuntimeError(f"first line\nsecond line leaked {api_key}"),
    )
    bounded = tui._normalize_llm_activation_error(RuntimeError("x" * 500))

    assert normalized == (
        "Initialization failed: RuntimeError: first line second line leaked sec***1234. "
        "Choose another model in /config."
    )
    assert api_key not in normalized
    assert "… Choose another model in /config." in bounded
    assert len(bounded) < 400


async def test_session_failure_does_not_enter_llm_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _llm_config()
    app = _app(config)
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

    await app._activate_llm_option(_selection(config))

    assert reported == [error]
    assert app._llm_activation_error is None


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

    _stub_app_startup(app, monkeypatch)
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
        assert not app.query_one("#input-bar", HistoryInput).disabled
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == [
            "✓ LLM off · /connect and the data explorer remain available.",
            "✓ LLM off · /connect and the data explorer remain available.",
        ]


async def test_startup_paints_banner_before_starting_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(None)
    started: list[bool] = []

    def fake_start(_selection: ResolvedLLMConfig) -> None:
        banner = app.query_one(BannerWidget)
        started.append(banner.query_one(".banner-art", Static).is_mounted)

    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_start_llm_activation", fake_start)

    async with app.run_test() as pilot:
        await pilot.pause()

        chat_log = app.query_one("#chat-log", VerticalScroll)
        assert [type(child) for child in chat_log.children[:2]] == [BannerWidget, SpinnerWidget]
        assert started == [True]


async def test_unconfigured_without_detected_key_explains_why_llm_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app_for_selection(_selection(None, inferred=True))

    async def fake_ensure_session() -> object:
        return _InactiveSession()

    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()

        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == ["✓ LLM off · no supported API key detected. Configure models in /config."]


async def test_inferred_startup_reports_masked_api_key_in_chat_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _llm_config(
        model="openai:gpt-5",
        reasoning="medium",
        subagent_model="openai:gpt-5-mini",
        subagent_reasoning="medium",
    )
    app = _app_for_selection(_selection(config, inferred=True, detected_api_key_env="OPENAI_API_KEY"))

    class FakeSession:
        def activate_llm_config(self, selected: LLMConfig) -> tuple[str | None, str | None]:
            assert selected == config
            return "sk-main123456789E0QA", "sk-main123456789E0QA"

    async def fake_ensure_session() -> object:
        return FakeSession()

    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == ["✓ OPENAI_API_KEY detected (sk-***E0QA) · using gpt-5. Change models in /config."]
        assert not app._llm_activation_in_progress
        assert not app.query_one("#input-bar", HistoryInput).disabled


async def test_failed_startup_activation_reports_error_and_unblocks_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _llm_config(model="anthropic:claude-opus-4-8", reasoning="high")
    app = _app(config)

    class FakeSession:
        def activate_llm_config(self, _selected: LLMConfig) -> tuple[str | None, str | None]:
            raise RuntimeError("missing credential")

    async def fake_ensure_session() -> object:
        return FakeSession()

    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages == [
            "LLM unavailable: Initialization failed: RuntimeError: missing credential. "
            "Choose another model in /config. Data connections and browsing remain available."
        ]
        assert app._llm_unavailable_message() == (
            "Initialization failed: RuntimeError: missing credential. "
            "Choose another model in /config. Data connections and browsing remain available."
        )
        assert not app._llm_activation_in_progress
        assert not app.query_one("#input-bar", HistoryInput).disabled


async def test_llm_activation_preserves_blocked_submissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(None)

    async def fake_ensure_session() -> object:
        return _InactiveSession()

    _stub_app_startup(app, monkeypatch)
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


async def test_submission_builds_ordered_multimodal_input(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    captured: list[tuple[object, str]] = []

    async def fake_run_submission(question: object, display_text: str, input_bar: HistoryInput | None) -> None:
        captured.append((question, display_text))

    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_run_submission", fake_run_submission)

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        input_bar = app.query_one("#input-bar", HistoryInput)
        image = BinaryContent(b"image", media_type="image/png")
        input_bar._active_images[1] = image
        input_bar._image_counter = 1
        input_bar.value = "inspect [Image #1] now"

        await pilot.press("enter")
        for _ in range(2):
            await pilot.pause()

    assert captured == [(["inspect [Image #1]", image, " now"], "inspect [Image #1] now")]


async def test_submission_displays_compact_paste_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)

    class _EmptyRegistry:
        def list_aliases(self) -> list[str]:
            return []

    class _Session:
        registry = _EmptyRegistry()

    async def fake_ensure_session() -> _Session:
        return _Session()

    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_start_llm_activation", lambda _selection: None)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)

    async with app.run_test():
        input_bar = app.query_one("#input-bar", HistoryInput)
        display_text = "inspect [Pasted text #1 +2 lines]"
        await app._run_submission("inspect pasted\ntext", display_text, input_bar)

        user_message = app.query_one(UserMessage)
        assert str(user_message.render()) == display_text


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

    _stub_app_startup(app, monkeypatch)
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


async def test_submission_worker_covers_and_can_cancel_session_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    preflight_started = asyncio.Event()
    release_preflight = asyncio.Event()

    async def initial_session() -> object:
        return _InactiveSession()

    _stub_app_startup(app, monkeypatch)
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
        image = BinaryContent(b"image", media_type="image/png")
        input_bar._active_images[1] = image
        input_bar._image_counter = 1
        input_bar.value = "show [Image #1]"
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
        assert input_bar.value == "show [Image #1]"
        assert input_bar._active_images == {1: image}
        messages = [str(message.render()) for message in app.query(SystemMessage)]
        assert messages[-1] == "Interrupted"


async def test_ctrl_c_only_interrupts_or_explains_how_to_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    exits: list[bool] = []
    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_request_exit", lambda: exits.append(True))

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()

        input_bar = app.query_one("#input-bar", HistoryInput)
        await pilot.press("ctrl+c", "ctrl+c")

        assert exits == []
        assert input_bar.placeholder == "Press Ctrl+D twice to quit"

        await pilot.press("ctrl+d")

        assert exits == []
        assert input_bar.placeholder == "Press Ctrl+D again to quit"

        await pilot.press("ctrl+d")

        assert exits == [True]


async def test_ctrl_d_preserves_active_work(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    exits: list[bool] = []
    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_request_exit", lambda: exits.append(True))

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()

        input_bar = app.query_one("#input-bar", HistoryInput)
        input_bar.value = "unfinished draft"
        await pilot.press("ctrl+d")

        assert input_bar.value == "unfinished draft"
        assert exits == []

        input_bar.clear()
        app._submission_worker = object()  # type: ignore[assignment]
        await pilot.press("ctrl+d")

        assert exits == []
        app._submission_worker = None

        await pilot.press("ctrl+d")
        input_bar.value = "changed my mind"
        input_bar.clear()
        await pilot.pause()
        await pilot.press("ctrl+d")

        assert exits == []


async def test_config_selection_persists_and_starts_one_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)
    session = _InactiveSession()
    updates: list[dict[str, object]] = []
    activations: list[ResolvedLLMConfig] = []

    async def fake_ensure_session() -> object:
        app._session = session  # type: ignore[assignment]
        return session

    _stub_app_startup(app, monkeypatch)
    monkeypatch.setattr(app, "_ensure_session", fake_ensure_session)
    monkeypatch.setattr(tui, "update_app_config", lambda **prefs: updates.append(prefs))

    async with app.run_test() as pilot:
        for _ in range(3):
            await pilot.pause()
        monkeypatch.setattr(app, "_start_llm_activation", activations.append)
        config = _llm_config(label="Selected")

        selection = ResolvedLLMConfig(config, config)
        app._on_config_closed(selection)
        await pilot.pause()

        assert session.selected_llm_config == config
        assert updates == [{"llm": config}]
        assert activations == [selection]


async def test_closing_config_restores_input_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(None)

    async def fake_ensure_session() -> object:
        return _InactiveSession()

    _stub_app_startup(app, monkeypatch)
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

        assert app.query_one("#input-bar", HistoryInput).has_focus
