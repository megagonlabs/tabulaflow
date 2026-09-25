"""Textual TUI application for tabulaflow interactive chat."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

from rich.console import Console
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.geometry import Offset
from textual.screen import Screen
from textual.timer import Timer
from textual.widget import Widget
from textual.worker import Worker
from textual.widgets import Button, Static

from tabulaflow.agents.llm import model_label
from tabulaflow.app.tui.commands import (
    CommandResult,
    HuggingFaceSubsetSelection,
    complete_hf_subset_selection,
    handle_command,
    is_registered_command,
    redact_command_credentials,
)
from tabulaflow.app.config import (
    LLMConfig,
    ResolvedLLMConfig,
    update_app_config,
)
from tabulaflow.app.model_catalog import ModelCatalog
from tabulaflow.app.tui.rendering import build_resolved_output_card_views
from tabulaflow.app.pane.cards import render_resolved_output
from tabulaflow.app.pane.contract import (
    PaneCard,
    PanePanel,
    manual_card_turn,
    pane_panel_for_output,
    turn_payload,
)
from tabulaflow.app.runtime_paths import RuntimePaths, ensure_pane_dir
from tabulaflow.app.sample_data import SAMPLE_ALIAS
from tabulaflow.app.session import WORKSPACE_ALIAS, AppSession
from tabulaflow.app.turn import TurnOutput
from tabulaflow.app.tui.theme import ERROR, FOCUS_SURFACE, KEY_HINT
from tabulaflow.app.tui.widgets.chat import BannerWidget, SpinnerWidget, SystemMessage, UserMessage
from tabulaflow.app.tui.widgets.chat_log import ChatLog
from tabulaflow.app.tui.widgets.choice import InlineChoiceSelector
from tabulaflow.app.tui.widgets.input import HistoryInput
from tabulaflow.app.tui.widgets.progress import AgentProgressWidget
from tabulaflow.app.tui.widgets.result import AgentResultWidget
from tabulaflow.app.tui.widgets.suggestions import InputSuggestionMenu

if TYPE_CHECKING:
    import pandas as pd

    from tabulaflow.agents.chat import ChatInput, ChatResult
    from tabulaflow.agents.llm import ServiceTier
    from tabulaflow.app.pane.server import BrowserPane
    from tabulaflow.output.resolver import ResolvedOutput

logger = logging.getLogger(__name__)

_REQUIRED_LLM_SETTINGS = frozenset({"GOOGLE_CLOUD_LOCATION", "GOOGLE_CLOUD_PROJECT"})
_LLM_SETTING_RE = re.compile(r"\b(?:[A-Z][A-Z0-9_]*_API_KEY|HF_TOKEN|HEROKU_INFERENCE_KEY|SNOWFLAKE_ACCOUNT)\b")
_MAX_ERROR_MESSAGE_LENGTH = 300
LLM_UNAVAILABLE_MESSAGE = "Configure models in /config. Data connections and browsing remain available."
_DEFAULT_INPUT_PLACEHOLDER = "Ask anything or type /connect"
_INTERRUPT_INPUT_PLACEHOLDER = "Ctrl+C to interrupt"
_COPY_HINT_DURATION = 1.5
_SAMPLE_DATA_PROMPT = "Show me a table and chart on sample data"
_TERMINAL_MODE_RESTORE_SEQUENCE = (
    "\x1b[?2004l"  # bracketed paste off
    "\x1b[?7h"  # line wrap on
    "\x1b[?1000l"  # mouse modes off
    "\x1b[?1002l"
    "\x1b[?1003l"
    "\x1b[?1015l"
    "\x1b[?1006l"
    "\x1b[<u"  # kitty keyboard protocol off
    "\x1b[?1049l"  # alt screen off
    "\x1b[?25h"  # cursor visible
    "\x1b[?1004l"  # focus reporting off
)


def _restore_terminal_modes() -> None:
    """Best-effort fallback for terminal private modes enabled by Textual."""
    import sys

    stream = sys.__stdout__
    if stream is None or not stream.isatty():
        return
    try:
        stream.write(_TERMINAL_MODE_RESTORE_SEQUENCE)
        stream.flush()
    except Exception:
        pass


class BottomSeparator(Static):
    """One-row separator that fills its current width without layout side effects."""

    def render(self) -> Text:
        return Text("━" * max(1, self.size.width), style="#333333", overflow="crop", no_wrap=True)


def _compact_project_dir(path: Path) -> str:
    """Return a compact display path for the project directory."""
    try:
        return f"~/{path.resolve().relative_to(Path.home()).as_posix()}"
    except ValueError:
        return path.resolve().as_posix()


def _pane_panel(result: "ChatResult") -> PanePanel | None:
    return pane_panel_for_output(result.output)


def _masked_api_key(key: str | None) -> str | None:
    """Return a masked API key suitable for display."""
    if key is None or len(key) < 12:
        return None
    return f"{key[:3]}***{key[-4:]}"


def _sanitize_exception_message(error: Exception) -> str:
    """Return a display-ready error sentence with environment API keys masked."""
    message = " ".join(str(error).split())
    for name, value in os.environ.items():
        if name.endswith("_API_KEY") and len(value) >= 12:
            message = message.replace(value, _masked_api_key(value) or "***")
    if len(message) > _MAX_ERROR_MESSAGE_LENGTH:
        return f"{message[: _MAX_ERROR_MESSAGE_LENGTH - 1].rstrip()}…"
    if message and not message.endswith((".", "!", "?", "…")):
        return f"{message}."
    return message


def _format_agent_turn_failure(error: Exception) -> str:
    """Return a sanitized turn failure message, falling back to its type."""
    message = _sanitize_exception_message(error)
    if message:
        return message
    return f"{type(error).__name__}."


def _normalize_llm_activation_error(error: Exception, *, model: str | None = None) -> str:
    """Return an actionable one-line explanation for an LLM activation error."""
    message = _sanitize_exception_message(error)
    if match := _LLM_SETTING_RE.search(message):
        setting = match.group()
        return f"{setting} is not set. Set it and restart TabulaFlow, or choose another model in /config."

    from google.auth.exceptions import DefaultCredentialsError

    if isinstance(error, DefaultCredentialsError):
        return (
            "Google Cloud credentials were not found. Configure Application Default Credentials and restart TabulaFlow."
        )

    if model is not None and model.startswith(("bedrock:", "bedrock-mantle:")) and "region" in message.casefold():
        return "AWS region is not set. Set AWS_REGION or AWS_DEFAULT_REGION and restart TabulaFlow."

    if isinstance(error, KeyError) and len(error.args) == 1 and error.args[0] in _REQUIRED_LLM_SETTINGS:
        setting = error.args[0]
        return f"{setting} is not set. Set it and restart TabulaFlow, or choose another model in /config."

    from pydantic_ai.exceptions import UserError

    if isinstance(error, UserError) or message.startswith(("Unknown model:", "Unknown provider:")):
        detail = message or f"{type(error).__name__}."
        return f"{detail} Choose another model in /config."
    detail = f"{type(error).__name__}: {message}" if message else f"{type(error).__name__}."
    return f"Initialization failed: {detail} Choose another model in /config."


def _llm_config_success_message(
    config: LLMConfig,
    keys: tuple[str | None, str | None],
    *,
    detected_api_key_env: str | None = None,
) -> Text:
    """Build the status message for an activated LLM configuration."""
    main_key, subagent_key = keys
    main_mask = _masked_api_key(main_key)
    subagent_mask = _masked_api_key(subagent_key)
    shared_key = main_key is not None and main_key == subagent_key

    if detected_api_key_env is not None:
        detected_key = main_key or subagent_key
        detected_mask = _masked_api_key(detected_key)
        detected = f"{detected_api_key_env} detected"
        if detected_mask is not None:
            detected += f" ({detected_mask})"
        return Text(
            f"✓ {detected} · using {model_label(config.main.model)}. Change models in /config.",
            style="dim",
        )

    message = Text("✓ Main: ", style="dim")
    message.append(f"{model_label(config.main.model)} · {config.main.effort}")
    if main_mask is not None and not shared_key:
        message.append(f" [API key {main_mask}]")
    message.append(" · Subagent: ")
    message.append(f"{model_label(config.subagent.model)} · {config.subagent.effort}")
    if subagent_mask is not None and not shared_key:
        message.append(f" [API key {subagent_mask}]")
    if shared_key and main_mask is not None:
        message.append(f" [API key {main_mask}]")
    return message


def _focused_has_binding_for(widget: object, key: str) -> bool:
    """True if ``widget`` (or any base class) declares a ``BINDINGS`` entry
    matching ``key``.

    Used by the app's typeahead handler to defer to the focused widget's
    own bindings for single-character keys like ``[`` / ``]`` / ``j`` /
    ``k`` instead of routing them to the input.
    """
    for cls in type(widget).__mro__:
        for binding_def in getattr(cls, "BINDINGS", ()):
            binding_key = binding_def[0] if isinstance(binding_def, tuple) else binding_def.key
            if binding_key == key:
                return True
    return False


class _SelectionGuardScreen(Screen[None]):
    """Ignore stale compositor hits until Textualize/textual#6643 is released.

    https://github.com/Textualize/textual/issues/6643
    """

    def get_widget_and_offset_at(self, x: int, y: int) -> tuple[Widget | None, Offset | None]:
        widget, offset = super().get_widget_and_offset_at(x, y)
        if widget is not None and not widget.is_attached:
            return None, None
        return widget, offset


class TabulaflowApp(App[None]):
    """Interactive data-source chat TUI."""

    CSS_PATH = "tui.tcss"

    def get_css_variables(self) -> dict[str, str]:
        """Register app-wide custom CSS variables.

        Defining variables here (rather than via ``$name: value;`` in
        tui.tcss) makes them visible from every stylesheet — including
        each widget's ``DEFAULT_CSS`` block, which is parsed separately
        and otherwise can't see top-level declarations from tui.tcss.
        """
        variables = super().get_css_variables()
        variables["focus-surface"] = FOCUS_SURFACE
        return variables

    BINDINGS = [
        ("ctrl+c", "interrupt_or_clear", "Interrupt / Clear"),
        ("ctrl+d", "confirm_quit", "Quit"),
        ("escape", "toggle_focus", "Toggle focus"),
        ("ctrl+o", "open_data_explorer", "Open data explorer"),
        Binding("pageup", "scroll_log('pageup')", "Scroll up", show=False, priority=True),
        Binding("pagedown", "scroll_log('pagedown')", "Scroll down", show=False, priority=True),
    ]

    def get_default_screen(self) -> _SelectionGuardScreen:
        return _SelectionGuardScreen(id="_default")

    _QUIT_CONFIRMATION_WINDOW = 2.0

    def __init__(
        self,
        *,
        llm_config: ResolvedLLMConfig,
        runtime_paths: RuntimePaths,
        project_dir: Path,
        llm_service_tier: ServiceTier = "default",
        enable_schema_cache: bool = False,
        log_level: int = logging.INFO,
        browser_pane_host: str = "127.0.0.1",
        browser_pane_port: int | None = None,
        browser_pane_public_url: str | None = None,
    ) -> None:
        import asyncio

        super().__init__()
        self.error_console = Console(color_system=None, markup=False, highlight=False, stderr=True)
        self._llm_config = llm_config
        self._llm_service_tier = llm_service_tier
        self._enable_schema_cache = enable_schema_cache
        self._log_level = log_level
        self._browser_pane_host = browser_pane_host
        self._browser_pane_port = browser_pane_port
        self._browser_pane_public_url = browser_pane_public_url
        self._runtime_paths = runtime_paths
        self._project_dir = project_dir
        self._model_catalog = ModelCatalog()
        self._session: AppSession | None = None
        self._browser_pane: BrowserPane | None = None
        self._session_lock = asyncio.Lock()
        self._llm_activation_in_progress = False
        self._llm_activation_error: str | None = None
        self._initialization_spinner: SpinnerWidget | None = SpinnerWidget("Initializing session...")
        self._submission_worker: Worker[None] | None = None
        self._pending_hf_subset_selection: HuggingFaceSubsetSelection | None = None
        self._last_quit_request_ts: float | None = None
        self._saved_input_placeholder: str | None = None
        self._input_hint_timer: Timer | None = None
        self._copy_hint_timer: Timer | None = None
        self._last_focused_result: AgentResultWidget | None = None
        # Session-scoped expansion + cursor state for the schema browser.
        # The same instance is passed to every SchemaBrowserScreen, which
        # mutates it on close so reopening lands the user where they left
        # off.
        from tabulaflow.app.tui.screens.schema import ExplorerState

        self._explorer_state = ExplorerState()

    def compose(self) -> ComposeResult:
        initialization_spinner = self._initialization_spinner
        assert initialization_spinner is not None
        with ChatLog(id="chat-log"):
            yield self._banner()
            yield initialization_spinner
        with Vertical(id="bottom-bar"):
            yield InputSuggestionMenu(id="input-suggestions")
            yield Static(Text("Copied to clipboard", style="dim"), id="copy-hint")
            yield BottomSeparator(classes="bottom-sep")
            with Horizontal(id="input-row"):
                yield HistoryInput(
                    history_path=self._runtime_paths.history_path,
                    placeholder=_SAMPLE_DATA_PROMPT,
                    empty_tab_completion=_SAMPLE_DATA_PROMPT,
                    id="input-bar",
                )
                with Vertical(id="explorer-control"):
                    # Disabled until the background session build + sample auto-connect
                    # completes (re-enabled at the end of ``_ensure_session``), so the user
                    # can't open an empty explorer before any data source is connected. While
                    # disabled it shows a "Preparing…" label so the fade reads as a
                    # transient loading state, not a permanently unavailable feature.
                    yield Button(self._explorer_label(ready=False), id="open-explorer-btn", disabled=True)
            yield BottomSeparator(classes="bottom-sep")
            with Horizontal(id="bottom-status"):
                yield Static(id="bottom-status-model")
                yield Static(id="bottom-status-url")

    def on_mount(self) -> None:
        self._setup_logging()
        chat_log = self.query_one("#chat-log", ChatLog)
        self.query_one("#input-bar", HistoryInput).focus()
        chat_log.follow_new_content(force=True)
        self._ensure_browser_pane()
        self.run_worker(self._model_catalog.warm(), exclusive=True, group="model-catalog")
        self.call_after_refresh(self._start_llm_activation, self._llm_config)

    def on_text_selected(self, event: events.TextSelected) -> None:
        """Auto-copy the chat selection to the clipboard when a drag ends.

        The terminal's mouse reporting routes the drag to us, so it can't make a
        native selection the user could copy with the terminal — so we copy the
        in-app selection ourselves on release (``TextSelected`` is not sent for
        Input/TextArea, which handle their own selection).
        """
        try:
            text = self.screen.get_selected_text()
            if text:
                self._copy_to_clipboard(text)
                self._show_copy_hint()
        except Exception:
            logger.warning("copying selected text failed", exc_info=True)
            self.screen.clear_selection()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        if isinstance(event.widget, AgentResultWidget):
            self._last_focused_result = event.widget

    def _copy_to_clipboard(self, text: str) -> None:
        """Write ``text`` to the system clipboard.

        Always emits OSC 52 (via Textual) so copy works over SSH and in terminals
        without a local clipboard tool; additionally pipes to a local tool when
        present, since macOS Terminal ignores OSC 52.
        """
        import shutil
        import subprocess
        import sys

        self.copy_to_clipboard(text)  # OSC 52

        if sys.platform == "darwin":
            cmd = ["pbcopy"]
        elif shutil.which("wl-copy"):
            cmd = ["wl-copy"]
        elif shutil.which("xclip"):
            cmd = ["xclip", "-selection", "clipboard"]
        else:
            return
        try:
            result = subprocess.run(cmd, input=text.encode("utf-8"), check=False)
        except OSError:
            logger.debug("native clipboard command failed", exc_info=True)
        else:
            if result.returncode:
                logger.debug("native clipboard command exited with status %d", result.returncode)

    def _show_copy_hint(self) -> None:
        self.query_one("#copy-hint", Static).styles.visibility = "visible"
        if self._copy_hint_timer is not None:
            self._copy_hint_timer.stop()
        self._copy_hint_timer = self.set_timer(_COPY_HINT_DURATION, self._hide_copy_hint)

    def _hide_copy_hint(self) -> None:
        self._copy_hint_timer = None
        self.query_one("#copy-hint", Static).styles.visibility = "hidden"

    def action_scroll_log(self, direction: str) -> None:
        """Page-scroll the chat log even when the input bar has focus.

        Textual's ``Input`` ignores PageUp/PageDown, so without this
        action those keys are a no-op while the user is typing.
        """
        if len(self.screen_stack) > 1:
            return
        try:
            chat_log = self.query_one("#chat-log", ChatLog)
        except Exception:
            return
        if direction == "pageup":
            chat_log.scroll_page_up()
        else:
            chat_log.scroll_page_down()

    def action_open_data_explorer(self) -> None:
        """Push the SchemaBrowserScreen — the canonical data explorer.

        Triggered by ``Ctrl+O`` from the input or by clicking the
        ``Open data explorer`` button next to the input. Until the session's
        workspace is ready it silently does nothing (the button keeps its normal
        look); once ready it falls back to a system message if nothing is connected.
        """
        from tabulaflow.app.tui.screens.schema import SchemaBrowserScreen
        from tabulaflow.app.tui.widgets.chat import SystemMessage

        if self._session is None:
            return  # workspace not ready yet — do nothing
        if not self._session.registry.list_aliases():
            chat_log = self.query_one("#chat-log", ChatLog)
            chat_log.mount(SystemMessage(Text("No data sources connected. Use /connect first.", style=ERROR)))
            chat_log.follow_new_content(force=True)
            return
        self.push_screen(
            SchemaBrowserScreen(
                registry=self._session.registry,
                alias=None,
                state=self._explorer_state,
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route the right-side button click to the data-explorer action."""
        if event.button.id == "open-explorer-btn":
            # Move focus to the input before pushing the explorer screen so
            # that popping back lands on the input, not the button (which
            # would otherwise keep its pressed/focus highlight).
            self.query_one("#input-bar", HistoryInput).focus()
            self.action_open_data_explorer()
            event.stop()

    def on_click(self, event: events.Click) -> None:
        """Reopen the browser pane when its URL row is clicked."""
        if getattr(event.widget, "id", None) != "bottom-status-url":
            return
        pane = self._browser_pane
        if pane is not None and pane.url is not None:
            pane.reopen()
            event.stop()

    def on_key(self, event: events.Key) -> None:
        """Typeahead-returns-focus: typing a printable character while
        focus is on any non-input widget (chat log, AgentResultWidget,
        etc.) snaps focus to the input bar and inserts the character.

        Pairs with the auto-focus-on-completion behavior: after the
        agent finishes, focus is on the latest result so Enter inspects.
        Starting to type a follow-up prompt returns the user to the
        input box without an explicit click or Tab.
        """
        focused = self.focused
        if focused is None or isinstance(focused, HistoryInput):
            return
        # Skip when a modal screen (CellBrowserScreen, DataBrowserScreen,
        # etc.) is open — those own their own keystrokes.
        if len(self.screen_stack) > 1:
            return
        # Modifier combos go to widget bindings, not the input.
        if "+" in event.key:
            return
        # Only printable single characters — filters Enter/Tab/Esc/etc.
        ch = event.character
        if ch is None or len(ch) != 1 or not ch.isprintable():
            return
        # Let the focused widget's own BINDINGS win — e.g. ``[`` and ``]``
        # for view nav on AgentResultWidget, or ``j``/``k`` for card
        # nav. Without this check, typeahead would steal those keys for
        # the input instead of triggering the widget's binding.
        if _focused_has_binding_for(focused, event.key):
            return
        inp = self.query_one("#input-bar", HistoryInput)
        new_value = inp.value + ch
        inp.value = new_value
        inp.cursor_position = len(new_value)
        inp.focus()
        event.stop()

    def _setup_logging(self) -> None:
        from logging.handlers import RotatingFileHandler

        log_dir = self._runtime_paths.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._runtime_paths.cli_log_path

        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(self._log_level)
        file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        root.addHandler(file_handler)
        logging.captureWarnings(True)

        for name in (
            "httpx",
            "httpx2",
            "httpcore",
            "urllib3",
            "grpc",
            "google",
            "google.auth",
            "google.api_core",
            "openai",
            "openai._base_client",
            "textual",
        ):
            lg = logging.getLogger(name)
            lg.handlers.clear()
            lg.propagate = True
            lg.setLevel(logging.WARNING)

        os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
        os.environ.setdefault("GLOG_minloglevel", "3")

    def action_interrupt_or_clear(self) -> None:
        """Ctrl+C:
        - If a submission is running: cancel it.
        - Else if the input has text: clear it.
        - Else: explain how to quit without arming the quit confirmation.
        """
        self._last_quit_request_ts = None
        if self._submission_worker is not None:
            self._submission_worker.cancel()
            self._clear_input_hint()
            return

        inp = self.query_one("#input-bar", HistoryInput)
        if inp.value:
            inp.value = ""
            self._clear_input_hint()
            # Land focus in the now-empty input so the user can compose
            # immediately. Matters when Ctrl+C is pressed while a result
            # widget is focused.
            inp.focus()
            return

        self._show_input_hint(inp, "Press Ctrl+D twice to quit")

    def on_text_area_changed(self, event: HistoryInput.Changed) -> None:
        """Disarm quit confirmation as soon as the prompt changes."""
        if not isinstance(event.text_area, HistoryInput) or event.text_area.id != "input-bar":
            return
        self._last_quit_request_ts = None
        if event.text_area.value:
            self._clear_input_hint()

    def action_confirm_quit(self) -> None:
        """Ctrl+D:
        - Do nothing while a submission or draft is active.
        - Else quit on a confirmed second press.
        """
        if self._submission_worker is not None:
            self._last_quit_request_ts = None
            self._clear_input_hint()
            return

        inp = self.query_one("#input-bar", HistoryInput)
        if inp.value:
            self._last_quit_request_ts = None
            self._clear_input_hint()
            return

        self._confirm_quit(inp)

    def _confirm_quit(self, inp: HistoryInput) -> None:
        """Quit only when Ctrl+D is pressed twice on an idle empty prompt."""
        import time

        now = time.monotonic()
        if (
            self._last_quit_request_ts is not None
            and (now - self._last_quit_request_ts) < self._QUIT_CONFIRMATION_WINDOW
        ):
            self._request_exit()
            return

        self._last_quit_request_ts = now
        self._show_input_hint(inp, "Press Ctrl+D again to quit")

    def _show_input_hint(self, inp: HistoryInput, message: str) -> None:
        """Temporarily replace the empty input's placeholder."""
        if self._saved_input_placeholder is None:
            self._saved_input_placeholder = cast(str, inp.placeholder)
        inp.placeholder = message
        if self._input_hint_timer is not None:
            self._input_hint_timer.stop()
        self._input_hint_timer = self.set_timer(self._QUIT_CONFIRMATION_WINDOW, self._restore_input_placeholder)

    def _request_exit(self) -> None:
        """Single quit path: disconnect all registered connectors, then
        exit the app. Every quit trigger (slash command, idle Ctrl+D
        double-press, …) routes through here so data-source connections
        and DuckDB file locks are always released cleanly.
        """
        if self._session is None:
            self._close_browser_pane()
            self.exit()
            return
        self.run_worker(self._shutdown_then_exit(), exclusive=False, group="shutdown")

    def _close_browser_pane(self, *, remove_artifacts: bool = False) -> None:
        """Stop the browser pane and optionally remove its session files."""
        if self._browser_pane is not None:
            self._browser_pane.stop()
            self._browser_pane = None
        if remove_artifacts:
            import shutil

            shutil.rmtree(self._runtime_paths.pane_dir, ignore_errors=True)

    async def _shutdown_then_exit(self) -> None:
        assert self._session is not None
        try:
            await self._session.close()
        except Exception:
            logger.warning("session close failed during exit", exc_info=True)
        finally:
            self._close_browser_pane()
            self.exit()

    def _ensure_browser_pane(self) -> "BrowserPane | None":
        """Start the browser pane if needed; return it, or None if it couldn't start."""
        if self._browser_pane is None:
            from tabulaflow.app.pane.server import BrowserPane

            try:
                ensure_pane_dir(self._runtime_paths.pane_dir)
                self._browser_pane = BrowserPane(
                    self._runtime_paths.pane_dir,
                    host=self._browser_pane_host,
                    port=self._browser_pane_port,
                    public_url=self._browser_pane_public_url,
                    session_id=self._runtime_paths.session_id,
                )
                self._browser_pane.start()
                self._refresh_bottom_status()
            except Exception:
                logger.warning("browser pane failed to start", exc_info=True)
                self._browser_pane = None
                self._refresh_bottom_status()
        return self._browser_pane

    def view_card_in_browser_pane(self, card: PaneCard, *, title: str | None = None) -> bool:
        """Push an already-written card-data payload to the pane."""
        pane = self._ensure_browser_pane()
        if pane is None or pane.url is None:
            return False
        try:
            pane.push(manual_card_turn(card, title=title))
        except Exception:
            logger.warning("publishing manual browser pane turn failed", exc_info=True)
            return False
        return True

    def show_table_in_browser_pane(self, df: pd.DataFrame, *, title: str) -> bool:
        """Render and show a table from a TUI screen in the browser pane."""
        from tabulaflow.app.pane.cards import ResultCardInput, render_result_data

        try:
            card = render_result_data(ResultCardInput(df=df, label=None), self._runtime_paths.pane_dir)
        except Exception:
            logger.warning("preparing manual table for browser pane failed", exc_info=True)
            return False
        return card is not None and self.view_card_in_browser_pane(card, title=title or "Table preview")

    def _refresh_bottom_status(self) -> None:
        """Show model status and the pane URL below the input row."""
        try:
            model_status = self.query_one("#bottom-status-model", Static)
            url_status = self.query_one("#bottom-status-url", Static)
        except Exception:
            return
        url = self._browser_pane.url if self._browser_pane is not None else None
        if self._llm_config.config is not None:
            main = self._llm_config.config.main
            model_status_label = model_label(main.model)
        else:
            model_status_label = "LLM off"
        model_status.update(Text(f"{model_status_label} · {_compact_project_dir(self._project_dir)}", style="dim"))
        url_status.update(Text(f"View in browser: {url}" if url else "", style="dim"))

    def _start_llm_activation(self, selection: ResolvedLLMConfig) -> None:
        """Initialize the confirmed LLM option in the background."""
        self._llm_activation_in_progress = selection.config is not None
        self._llm_activation_error = None
        self.run_worker(
            self._activate_llm_option(selection),
            exclusive=True,
            group="llm-activation",
        )

    async def _activate_llm_option(self, selection: ResolvedLLMConfig) -> None:
        """Activate a confirmed LLM configuration or LLM off."""
        import asyncio

        config = selection.config
        if self._session is None:
            await self._show_initialization_spinner("Initializing session...")
        try:
            session = await self._ensure_session()
        except Exception as error:
            logger.exception("session initialization failed")
            await self._report_session_initialization_failure(error)
            return
        if config is None:
            session.activate_llm_config(None)
            if selection.selection is None:
                status = "✓ LLM off · no OpenAI or Anthropic API key detected. Choose models in /config."
            else:
                status = "✓ LLM off · /connect and the data explorer remain available."
            await self._publish_initialization_status(
                Text(status, style="dim"),
            )
            return
        await self._show_initialization_spinner("Initializing agent...")
        try:
            keys = await asyncio.to_thread(session.activate_llm_config, config)
        except Exception as error:
            logger.exception("LLM configuration initialization failed")
            await self._finish_llm_activation(selection, result=error)
            return
        await self._finish_llm_activation(selection, result=keys)

    async def _show_initialization_spinner(self, label: str) -> None:
        if self._initialization_spinner is not None:
            self._initialization_spinner.update_label(label)
            return
        spinner = SpinnerWidget(label)
        self._initialization_spinner = spinner
        chat_log = self.query_one("#chat-log", ChatLog)
        await chat_log.mount(spinner)
        chat_log.follow_new_content()

    async def _remove_initialization_spinner(self) -> None:
        spinner = self._initialization_spinner
        self._initialization_spinner = None
        if spinner is not None:
            await spinner.remove()

    async def _publish_initialization_status(self, message: Text) -> None:
        """Replace the initialization spinner with ``message``."""
        await self._remove_initialization_spinner()
        chat_log = self.query_one("#chat-log", ChatLog)
        await chat_log.mount(SystemMessage(message))
        chat_log.follow_new_content()

    async def _report_session_initialization_failure(self, error: Exception) -> None:
        message = Text.from_markup(f"[{ERROR}]Session initialization failed:[/] ")
        detail = _sanitize_exception_message(error)
        message.append(f"{type(error).__name__}: {detail}" if detail else f"{type(error).__name__}.")
        await self._publish_initialization_status(message)
        self._llm_activation_in_progress = False

    async def _finish_llm_activation(
        self,
        selection: ResolvedLLMConfig,
        *,
        result: tuple[str | None, str | None] | Exception,
    ) -> None:
        config = selection.config
        if config is None:
            raise RuntimeError("Cannot finish activation without an LLM configuration.")
        if isinstance(result, Exception):
            self._llm_activation_error = _normalize_llm_activation_error(result, model=config.main.model)
            message = Text.from_markup(f"[{ERROR}]LLM unavailable:[/] ")
            message.append(self._llm_unavailable_message())
        else:
            self._llm_activation_error = None
            message = _llm_config_success_message(
                config,
                result,
                detected_api_key_env=selection.detected_api_key_env,
            )
        await self._publish_initialization_status(message)
        self._llm_activation_in_progress = False
        input_bar = self.query_one("#input-bar", HistoryInput)
        if len(self.screen_stack) == 1:
            input_bar.focus()

    def _llm_unavailable_message(self) -> str:
        if self._llm_activation_error is None:
            return LLM_UNAVAILABLE_MESSAGE
        return f"{self._llm_activation_error} Data connections and browsing remain available."

    async def _push_turn_to_browser_pane(
        self,
        result: "ChatResult",
        resolved_output: "ResolvedOutput",
        turn_output: TurnOutput,
        *,
        title: str,
        user_text: str,
        pane: "BrowserPane | None" = None,
        turn_id: int | None = None,
    ) -> None:
        """Render a completed turn and push it to the browser pane.

        The pane starts during TUI mount so the URL is available before an
        agent run; completed turns update it silently. Best-effort — any failure
        is swallowed so the pane never blocks or fails a chat turn.
        """
        import asyncio

        pane_dir = self._runtime_paths.pane_dir
        try:
            ensure_pane_dir(pane_dir)
        except Exception:
            logger.warning("preparing browser pane directory failed (turn_id=%s)", turn_id, exc_info=True)
            if pane is not None and turn_id is not None:
                pane.discard_turn(turn_id)
            return
        if not resolved_output.artifacts and not user_text and not result.text:
            if pane is not None and turn_id is not None:
                pane.discard_turn(turn_id)
            return
        pane = pane or self._ensure_browser_pane()
        if pane is None:
            return

        panel = _pane_panel(result)

        async def render_and_push() -> None:
            try:
                cards = await render_resolved_output(resolved_output, pane_dir)
                payload = turn_payload(title=title, user=user_text, assistant=result.text, cards=cards, panel=panel)
                if turn_id is None:
                    pane.push(payload, turn_output=turn_output if panel is not None else None)
                else:
                    pane.complete_turn(turn_id, payload, turn_output=turn_output if panel is not None else None)
            except Exception:
                if turn_id is not None:
                    pane.discard_turn(turn_id)
                raise

        def log_background_error(task: asyncio.Task[None]) -> None:
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                return
            if exc is not None:
                logger.warning(
                    "browser pane finalization failed (turn_id=%s)",
                    turn_id,
                    exc_info=(type(exc), exc, exc.__traceback__),
                )

        task = asyncio.create_task(render_and_push())
        task.add_done_callback(log_background_error)

    def _restore_input_text(self, text: str) -> None:
        """Put `text` back into the input bar and focus it. Used after a
        cancelled turn so the user can edit and resubmit. If the input
        already has content (the user started typing something new during
        the turn), leave it alone."""
        try:
            inp = self.query_one("#input-bar", HistoryInput)
        except Exception:
            return
        if inp.value:
            return
        inp.value = text
        inp.cursor_position = len(text)
        inp.focus()

    def _restore_input_placeholder(self) -> None:
        self._input_hint_timer = None
        if self._saved_input_placeholder is None:
            return
        try:
            inp = self.query_one("#input-bar", HistoryInput)
        except Exception:
            return
        inp.placeholder = self._saved_input_placeholder
        self._saved_input_placeholder = None

    def _clear_input_hint(self) -> None:
        """Restore the normal input placeholder immediately."""
        if self._input_hint_timer is not None:
            self._input_hint_timer.stop()
            self._input_hint_timer = None
        self._restore_input_placeholder()

    def action_toggle_focus(self) -> None:
        """Toggle focus between input bar and result widgets."""
        inp = self.query_one("#input-bar", HistoryInput)
        if inp.has_focus:
            results = list(self.query(AgentResultWidget))
            if not results:
                return
            target = self._last_focused_result
            if target not in results:
                target = results[-1]
            target.focus()
            target.scroll_visible()
        else:
            inp.focus()

    async def _ensure_session(self) -> AppSession:
        """Return the session, creating its non-visual runtime once."""
        if self._session is not None:
            return self._session

        async with self._session_lock:
            if self._session is not None:
                return self._session
            session = await AppSession.create(
                llm_config=self._llm_config.config,
                runtime_paths=self._runtime_paths,
                project_dir=self._project_dir,
                llm_service_tier=self._llm_service_tier,
                enable_schema_cache=self._enable_schema_cache,
            )
            self._enable_explorer_button()
            # Publish the session only once it is fully ready (sample autoconnected,
            # explorer enabled). The early-return guards above key off ``self._session``,
            # so setting it sooner would let an early question proceed mid-setup.
            self._session = session
            self._refresh_bottom_status()
            return self._session

    @staticmethod
    def _explorer_label(*, ready: bool) -> Text:
        """Build the explorer button label for its loading vs. ready state."""
        label = Text()
        if ready:
            label.append("Ctrl+O", style=KEY_HINT)
            label.append("  Open data explorer", style="dim")
        else:
            label.append("Preparing workspace…", style="dim")
        return label

    def _enable_explorer_button(self) -> None:
        """Enable the data-explorer button once the session (and sample) are ready."""
        try:
            btn = self.query_one("#open-explorer-btn", Button)
            btn.label = self._explorer_label(ready=True)
            btn.disabled = False
        except Exception:
            pass

    async def on_history_input_submitted(self, event: HistoryInput.Submitted) -> None:
        display_text = event.value.strip()
        if not display_text:
            return

        inp = event.input
        if self._submission_worker is not None or self._llm_activation_in_progress:
            inp.focus()
            return

        question = inp.build_chat_input(display_text)
        if not isinstance(question, str) and is_registered_command(display_text):
            inp.notify("Images cannot be attached to slash commands", severity="error")
            return

        _, contains_credentials = redact_command_credentials(display_text) if is_registered_command(display_text) else (display_text, False)
        inp.record_submission(display_text, persist=not contains_credentials)
        inp.clear()
        inp.placeholder = _DEFAULT_INPUT_PLACEHOLDER
        inp.clear_empty_tab_completion()

        self._submission_worker = self.run_worker(
            self._run_submission(question, display_text, inp),
            exclusive=True,
            group="submission",
        )

    async def _run_submission(
        self,
        question: "ChatInput",
        display_text: str,
        input_bar: HistoryInput | None,
    ) -> None:
        """Process one accepted input as the active submission."""
        import asyncio

        chat_log = self.query_one("#chat-log", ChatLog)
        is_command = isinstance(question, str) and is_registered_command(question)
        visible_text = redact_command_credentials(display_text)[0] if is_command else display_text
        user_msg = UserMessage(visible_text)
        interrupted = False
        if input_bar is not None:
            input_bar.placeholder = _INTERRUPT_INPUT_PLACEHOLDER
        try:
            await chat_log.mount(user_msg)
            chat_log.follow_new_content(force=True)

            if is_command:
                assert isinstance(question, str)
                await self._handle_slash_command(question, chat_log)
                return

            session = await self._ensure_session()
            if not session.registry.list_aliases():
                msg = SystemMessage(Text.from_markup(f"[{ERROR}]No data source connected.[/] Use /connect first."))
                await chat_log.mount(msg)
                chat_log.follow_new_content()
                return

            if not session.llm_available:
                error_text = Text.from_markup(f"[{ERROR}]LLM unavailable:[/] ")
                error_text.append(self._llm_unavailable_message())
                await chat_log.mount(SystemMessage(error_text))
                chat_log.follow_new_content()
                self._refresh_bottom_status()
                return

            await self._run_agent(question, session, chat_log, display_text)
        except asyncio.CancelledError:
            interrupted = True
            if is_command and user_msg.is_mounted:
                await user_msg.remove()
            await chat_log.mount(SystemMessage("[dim]Interrupted[/dim]"))
            chat_log.follow_new_content()
            self._restore_input_text(display_text)
            raise
        finally:
            if input_bar is not None:
                input_bar.placeholder = _DEFAULT_INPUT_PLACEHOLDER
                if not interrupted:
                    input_bar.release_submission_images(display_text)
            self._submission_worker = None

    @staticmethod
    async def _connect_spinner_label(parts: list[str]) -> str:
        """Build a spinner label for /connect."""
        return "Connecting..."

    async def _handle_slash_command(
        self,
        text: str,
        chat_log: ChatLog,
    ) -> None:
        parts = text.split()
        cmd = parts[0].lower() if parts else ""
        slow = cmd in {"/connect", "/disconnect"} and len(parts) > 1

        spinner: SpinnerWidget | None = None
        if slow:
            label = "Connecting..." if cmd == "/connect" else "Disconnecting..."
            spinner = SpinnerWidget(label)
            # Await the mount: a fast-failing handle_command (e.g. validation
            # error) may return without yielding, never giving the event loop
            # a chance to process a non-awaited mount before we hit the
            # ``finally`` — leaving the spinner queued-but-not-removed.
            await chat_log.mount(spinner)
            chat_log.follow_new_content()
            # Refine label with dataset size info (non-blocking).
            if cmd == "/connect":
                refined = await self._connect_spinner_label(parts)
                if spinner._label != refined:
                    spinner.update_label(refined)

        try:
            session = await self._ensure_session()
            result = await handle_command(text, session)
        finally:
            if spinner is not None:
                await spinner.remove()

        await self._show_command_result(result, session, chat_log)
        self._refresh_bottom_status()

    async def _show_command_result(
        self,
        result: CommandResult,
        session: AppSession,
        chat_log: ChatLog,
    ) -> None:
        if result.action == "quit":
            self._request_exit()
            return

        if result.action == "clear":
            await chat_log.remove_children()
            await chat_log.mount(self._banner())
            aliases = [
                alias for alias in session.registry.list_aliases() if alias not in {WORKSPACE_ALIAS, SAMPLE_ALIAS}
            ]
            if aliases:
                connected = Text("Connected sources: ", style="dim")
                connected.append(", ".join(aliases), style="bold dim")
                await chat_log.mount(SystemMessage(connected))
            if self._browser_pane is not None:
                try:
                    self._browser_pane.clear()
                except Exception:
                    logger.warning("clearing browser pane failed", exc_info=True)
            return

        if result.action == "open_config":
            from tabulaflow.app.tui.screens.config import ConfigScreen

            self.push_screen(
                ConfigScreen(self._llm_config, catalog_loader=self._model_catalog.get),
                self._on_config_closed,
            )
            return

        if isinstance(result.action, HuggingFaceSubsetSelection):
            selection = result.action
            self._pending_hf_subset_selection = selection
            self.query_one("#input-bar", HistoryInput).disabled = True
            await chat_log.mount(
                InlineChoiceSelector(
                    "Choose subset",
                    selection.subsets,
                    confirm_label="Connect",
                )
            )
            chat_log.follow_new_content(force=True)
            return

        if result.output is not None:
            msg = SystemMessage(result.output)
            await chat_log.mount(msg)
            chat_log.follow_new_content()

    async def on_inline_choice_selector_selected(self, event: InlineChoiceSelector.Selected) -> None:
        selection = self._pending_hf_subset_selection
        if selection is None:
            return
        self._pending_hf_subset_selection = None
        await self.query_one(InlineChoiceSelector).remove()
        self._restore_input_after_choice()
        self._submission_worker = self.run_worker(
            self._run_hf_subset_connection(selection, event.value),
            exclusive=True,
            group="submission",
        )

    async def _run_hf_subset_connection(
        self,
        selection: HuggingFaceSubsetSelection,
        subset: str,
    ) -> None:
        import asyncio

        chat_log = self.query_one("#chat-log", ChatLog)
        spinner = SpinnerWidget("Connecting...")
        await chat_log.mount(spinner)
        chat_log.follow_new_content(force=True)
        try:
            session = await self._ensure_session()
            result = await complete_hf_subset_selection(selection, subset, session)
            await spinner.remove()
            await self._show_command_result(result, session, chat_log)
            self._refresh_bottom_status()
        except asyncio.CancelledError:
            if spinner.is_mounted:
                await spinner.remove()
            await chat_log.mount(SystemMessage(Text("Interrupted", style="dim")))
            chat_log.follow_new_content()
            raise
        finally:
            if spinner.is_mounted:
                await spinner.remove()
            self._submission_worker = None

    async def on_inline_choice_selector_cancelled(self, event: InlineChoiceSelector.Cancelled) -> None:
        if self._pending_hf_subset_selection is None:
            return
        self._pending_hf_subset_selection = None
        await self.query_one(InlineChoiceSelector).remove()
        chat_log = self.query_one("#chat-log", ChatLog)
        await chat_log.mount(SystemMessage(Text("Connection cancelled.", style="dim")))
        chat_log.follow_new_content(force=True)
        self._restore_input_after_choice()

    def _restore_input_after_choice(self) -> None:
        input_bar = self.query_one("#input-bar", HistoryInput)
        input_bar.disabled = False
        input_bar.focus()

    def _on_config_closed(self, selection: ResolvedLLMConfig | None) -> None:
        self.call_after_refresh(self.query_one("#input-bar", HistoryInput).focus)
        if selection is None:
            return

        session = self._session
        if session is None:
            raise RuntimeError("Config closed before the session was initialized.")
        if selection.config is not None:
            session.apply_llm_request_rate(selection.config.requests_per_minute)
        session.select_llm_config(selection.config)
        self._llm_config = selection
        update_app_config(llm=selection.selection)
        self._refresh_bottom_status()
        self._start_llm_activation(selection)

    async def _run_agent(
        self,
        question: "ChatInput",
        session: AppSession,
        chat_log: ChatLog,
        display_text: str,
    ) -> None:
        import asyncio

        from tabulaflow.agents.chat import TurnFinished

        pane = self._ensure_browser_pane()
        pane_turn_id: int | None = None
        if pane is not None:
            try:
                pane_turn_id = pane.begin_turn(title=display_text, user=display_text)
            except Exception:
                logger.warning("publishing pending browser pane turn failed", exc_info=True)

        progress = AgentProgressWidget()
        await chat_log.mount(progress)
        chat_log.follow_new_content()

        result: ChatResult | None = None
        try:
            async for event in session.run_stream(question):
                await progress.apply(event)
                chat_log.follow_new_content()
                if isinstance(event, TurnFinished):
                    result = event.result
        except asyncio.CancelledError:
            # Freeze the partial progress widget; ChatSession's message history and
            # last_usage already reflect the interrupted run.
            await progress.mark_interrupted(session.last_usage)
            chat_log.follow_new_content()
            if pane is not None and pane_turn_id is not None:
                pane.discard_turn(pane_turn_id)
            raise
        except Exception as e:
            logger.exception("agent turn failed (pane_turn_id=%s)", pane_turn_id)
            # Freeze the partial progress widget (mirrors the interrupt path) so the
            # tool steps run so far stay visible, then mount the error below it.
            await progress.mark_failed()
            # Build the detail as plain text (not interpolated into markup) so a
            # ``[...]`` in the exception message can't be parsed as a markup tag.
            error_text = Text.from_markup(f"[{ERROR}]Agent turn failed:[/] ")
            error_text.append(_format_agent_turn_failure(e))
            msg = SystemMessage(error_text)
            await chat_log.mount(msg)
            chat_log.follow_new_content()
            if pane is not None and pane_turn_id is not None:
                pane.discard_turn(pane_turn_id)
            return
        if result is None:
            if pane is not None and pane_turn_id is not None:
                pane.discard_turn(pane_turn_id)
            return  # normal completion always yields a terminal TurnFinished

        try:
            turn_output = session.turn_output(result.output)
            resolved_output = await turn_output.resolve()
        except Exception:
            logger.exception("preparing completed turn failed (pane_turn_id=%s)", pane_turn_id)
            if pane is not None and pane_turn_id is not None:
                pane.discard_turn(pane_turn_id)
            raise
        await self._push_turn_to_browser_pane(
            result,
            resolved_output,
            turn_output,
            title=display_text,
            user_text=display_text,
            pane=pane,
            turn_id=pane_turn_id,
        )
        cards = build_resolved_output_card_views(resolved_output, self.size.width - 11)
        if cards:
            # chat-log padding (2) + scrollbar (2) + widget margin (5) + widget padding (2) = 11
            result_widget = AgentResultWidget(
                result,
                cards,
                turn_output=turn_output,
            )
            await chat_log.mount(result_widget)
            # Focus the just-mounted result so the user can press Enter to
            # inspect it without first clicking. The typeahead handler in
            # ``on_key`` routes any printable keystroke back to the input,
            # so this doesn't block fast follow-up prompts. Skip the steal
            # when the user is already composing in the input — yanking
            # focus mid-typing would be hostile.
            inp = self.query_one("#input-bar", HistoryInput)
            if chat_log.following_tail and not inp.value:
                result_widget.focus(scroll_visible=False)

        chat_log.follow_new_content()

    @staticmethod
    def _banner() -> BannerWidget:
        return BannerWidget()


async def run_tui(
    llm_config: ResolvedLLMConfig,
    *,
    llm_service_tier: ServiceTier = "default",
    enable_schema_cache: bool = False,
    log_level: int = logging.INFO,
    browser_pane_host: str = "127.0.0.1",
    browser_pane_port: int | None = None,
    browser_pane_public_url: str | None = None,
) -> None:
    """Launch the Textual TUI app."""
    app = TabulaflowApp(
        llm_config=llm_config,
        runtime_paths=RuntimePaths.create(),
        project_dir=Path.cwd(),
        llm_service_tier=llm_service_tier,
        enable_schema_cache=enable_schema_cache,
        log_level=log_level,
        browser_pane_host=browser_pane_host,
        browser_pane_port=browser_pane_port,
        browser_pane_public_url=browser_pane_public_url,
    )
    try:
        await app.run_async(mouse=True)
    finally:
        app._close_browser_pane(remove_artifacts=True)
        _restore_terminal_modes()
