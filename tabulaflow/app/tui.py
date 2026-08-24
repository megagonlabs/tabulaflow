"""Textual TUI application for tabulaflow interactive chat."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.worker import Worker
from textual.widgets import Button, Input, Static

from tabulaflow.app.commands import COMMAND_PREFIX, handle_command
from tabulaflow.app.config import (
    PROVIDER_API_KEY_ENV,
    LLMPreset,
    ResolvedLLMSelection,
    update_app_config,
)
from tabulaflow.app.debug import debug_enabled, mount_debug_widgets
from tabulaflow.app.display import build_resolved_output_card_views
from tabulaflow.app.pane import (
    PaneCard,
    PanePanel,
    manual_card_turn,
    pane_panel_for_output,
    render_resolved_output,
    turn_payload,
)
from tabulaflow.app.runtime_paths import RuntimePaths, ensure_pane_dir
from tabulaflow.app.state import LLM_UNAVAILABLE_MESSAGE, AppState
from tabulaflow.app.turn import TurnOutput
from tabulaflow.agents.llm import model_display_name
from tabulaflow.app.theme import ERROR, FOCUS_SURFACE, KEY_HINT
from tabulaflow.app.widgets import (
    AgentProgressWidget,
    AgentResultWidget,
    BannerWidget,
    HistoryInput,
    SpinnerWidget,
    SystemMessage,
    UserMessage,
)

if TYPE_CHECKING:
    from tabulaflow.app.pane import OutputPane
    from tabulaflow.agents.chat import ChatSession, ChatResult
    from tabulaflow.output.resolver import ResolvedOutput

logger = logging.getLogger(__name__)

_REQUIRED_LLM_SETTINGS = frozenset({"GOOGLE_CLOUD_LOCATION", "GOOGLE_CLOUD_PROJECT"})
_MAX_ERROR_MESSAGE_LENGTH = 300
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


def _normalize_llm_activation_error(error: Exception, preset: LLMPreset) -> str:
    """Return an actionable one-line explanation for an LLM activation error."""
    message = _sanitize_exception_message(error)
    for role in (preset.main, preset.subagent):
        provider = role.model.partition(":")[0]
        if setting := PROVIDER_API_KEY_ENV.get(provider):
            if setting in message:
                return f"{setting} is not set. Set it and restart the app, or choose another preset in /config."

    if isinstance(error, KeyError) and len(error.args) == 1 and error.args[0] in _REQUIRED_LLM_SETTINGS:
        setting = error.args[0]
        return f"{setting} is not set. Set it and restart the app, or choose another preset in /config."

    from pydantic_ai.exceptions import UserError

    if isinstance(error, UserError) or message.startswith(("Unknown model:", "Unknown provider:")):
        detail = message or f"{type(error).__name__}."
        return f"{detail} Update app_config.json or choose another preset in /config."
    detail = f"{type(error).__name__}: {message}" if message else f"{type(error).__name__}."
    return f"Initialization failed: {detail} Choose another preset in /config."


def _llm_preset_success_message(
    preset: LLMPreset,
    keys: tuple[str | None, str | None],
    *,
    detected_api_key_env: str | None = None,
) -> Text:
    """Build the status message for an activated LLM preset."""
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
            f"✓ {detected} · using {preset.label}. Change the preset in /config.",
            style="dim",
        )

    message = Text(f"✓ LLM preset: {preset.label} · ", style="dim")
    message.append(model_display_name(preset.main.model, preset.main.reasoning_effort))
    if main_mask is not None and not shared_key:
        message.append(f" [API key {main_mask}]")
    message.append(" → ")
    message.append(model_display_name(preset.subagent.model, preset.subagent.reasoning_effort))
    if subagent_mask is not None and not shared_key:
        message.append(f" [API key {subagent_mask}]")
    if shared_key and main_mask is not None:
        message.append(f" [API key {main_mask}]")
    return message


def _warm_session_imports() -> None:
    """Import the workspace connector's sqlalchemy/duckdb stack off the UI thread.

    ``create_workspace_connector`` runs on the main event loop (the async engine is
    loop-bound), so its first import of this stack (~0.7s cold) would briefly freeze
    the UI during the background session build. Warming it in the executor first keeps
    the UI responsive. The agent's other heavy imports happen in the executor-thread
    ``AppState`` construction, so they need no warming here."""
    import tabulaflow.data.sql  # noqa: F401


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


class TabulaflowApp(App[None]):
    """Interactive database chat TUI."""

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
        ("ctrl+c", "interrupt_or_quit", "Interrupt / Quit"),
        ("ctrl+d", "quit_only", "Quit"),
        ("escape", "toggle_focus", "Toggle focus"),
        ("ctrl+o", "open_data_explorer", "Open data explorer"),
        Binding("pageup", "scroll_log('pageup')", "Scroll up", show=False, priority=True),
        Binding("pagedown", "scroll_log('pagedown')", "Scroll down", show=False, priority=True),
    ]

    _INTERRUPT_DOUBLE_PRESS_WINDOW = 1.0

    def __init__(
        self,
        *,
        llm_selection: ResolvedLLMSelection,
        output_pane_host: str = "127.0.0.1",
        output_pane_port: int | None = None,
        output_pane_public_url: str | None = None,
    ) -> None:
        import asyncio

        super().__init__()
        self._llm_selection = llm_selection
        self._output_pane_host = output_pane_host
        self._output_pane_port = output_pane_port
        self._output_pane_public_url = output_pane_public_url
        self._runtime_paths = RuntimePaths.create()
        # The directory the app was launched from — the user's project, where source
        # data lives and what relative paths resolve against. Captured once at startup.
        # INVARIANT: the process must never chdir. The shell tool uses this captured
        # value as its cwd, while in-process run_query/DuckDB (COPY, read_csv_auto, …)
        # resolve relative paths against the *live* process cwd; the "relative = project
        # dir" design holds only while those two stay equal, i.e. cwd never changes.
        self._project_dir = Path(os.getcwd())
        ensure_pane_dir(self._runtime_paths.pane_dir)
        self._session: AppState | None = None
        self._pane: OutputPane | None = None
        self._session_lock = asyncio.Lock()
        self._llm_activation_in_progress = False
        self._llm_activation_error: str | None = None
        self._initialization_spinner: SpinnerWidget | None = None
        self._submission_worker: Worker[None] | None = None
        self._last_idle_interrupt_ts: float = 0.0
        self._saved_input_placeholder: str | None = None
        self._last_quit_hint_key: str = "Ctrl+C"
        # Session-scoped expansion + cursor state for the schema browser.
        # The same instance is passed to every SchemaBrowserScreen, which
        # mutates it on close so reopening lands the user where they left
        # off.
        from tabulaflow.app.screens import _ExplorerState

        self._explorer_state = _ExplorerState()

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat-log")
        with Vertical(id="bottom-bar"):
            yield BottomSeparator(classes="bottom-sep")
            with Horizontal(id="input-row"):
                yield Static("┃", id="input-prompt")
                yield HistoryInput(
                    history_path=self._runtime_paths.history_path,
                    placeholder="Ask a question or type /help",
                    id="input-bar",
                )
                yield Static("│", classes="input-sep")
                # Content set by ``_refresh_esc_hint`` once mounted; starts disabled
                # (faded) until there are results to jump to.
                yield Static(id="input-esc-hint", disabled=True)
                yield Static("│", classes="input-sep")
                # Disabled until the background session build + sample auto-connect
                # completes (re-enabled at the end of ``_ensure_session``), so the user
                # can't open an empty explorer before any database is connected. While
                # disabled it shows a "Preparing…" label so the fade reads as a
                # transient loading state, not a permanently unavailable feature.
                yield Button(self._explorer_label(ready=False), id="open-explorer-btn", disabled=True)
            yield BottomSeparator(classes="bottom-sep")
            with Horizontal(id="bottom-status"):
                yield Static(id="bottom-status-model")
                yield Static(id="bottom-status-url")

    def on_mount(self) -> None:
        self._setup_logging()
        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.mount(self._banner_for_preset(self._llm_selection.preset))
        if debug_enabled():
            mount_debug_widgets(self, chat_log)
        self.query_one("#input-bar", Input).focus()
        chat_log.scroll_end(animate=False)
        self._refresh_esc_hint()
        self._ensure_pane()
        self._start_llm_activation(self._llm_selection)

    def _refresh_esc_hint(self) -> None:
        """Update the docked ``Esc`` hint label to match current state.

        The label flips between ``Go to results`` (when focus is on the
        input) and ``Go to input`` (when focus is on a result widget). When no
        result widgets exist yet the hint is ``disabled`` — its ``:disabled``
        CSS fades it exactly like the disabled ``Open data explorer`` button, so
        the two input-row hints read consistently.
        """
        try:
            hint = self.query_one("#input-esc-hint", Static)
        except Exception:
            return
        has_results = bool(self.query(AgentResultWidget))
        in_result = isinstance(self.focused, AgentResultWidget)
        label = Text()
        label.append("Esc", style=KEY_HINT)
        label.append("  Go to input" if in_result else "  Go to results", style="dim")
        hint.update(label)
        hint.disabled = not has_results

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        """Re-render the Esc hint when focus moves between input/results."""
        self._refresh_esc_hint()

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
        except Exception:
            logger.warning("copying selected text failed", exc_info=True)
            self.screen.clear_selection()

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

    def action_scroll_log(self, direction: str) -> None:
        """Page-scroll the chat log even when the input bar has focus.

        Textual's ``Input`` ignores PageUp/PageDown, so without this
        action those keys are a no-op while the user is typing.
        """
        if len(self.screen_stack) > 1:
            return
        try:
            chat_log = self.query_one("#chat-log", VerticalScroll)
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
        from tabulaflow.app.screens import SchemaBrowserScreen
        from tabulaflow.app.widgets import SystemMessage

        if self._session is None:
            return  # workspace not ready yet — do nothing
        if not self._session.registry.list_aliases():
            chat_log = self.query_one("#chat-log", VerticalScroll)
            chat_log.mount(SystemMessage(Text("No databases connected. Use /connect first.", style=ERROR)))
            chat_log.scroll_end(animate=False)
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
            self.query_one("#input-bar", Input).focus()
            self.action_open_data_explorer()
            event.stop()

    def on_click(self, event: events.Click) -> None:
        """Reopen the output pane when the persistent pane URL row is clicked."""
        if getattr(event.widget, "id", None) != "bottom-status-url":
            return
        pane = self._pane
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
        if focused is None or isinstance(focused, Input):
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
        inp = self.query_one("#input-bar", Input)
        # Textual's ``Input`` auto-selects all existing text on focus, so
        # ``insert_text_at_cursor`` would *replace* the user's in-progress
        # composition. Append directly to ``value`` and move the cursor
        # to the end — keeps any existing text and tacks on the typed
        # character.
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
        root.setLevel(logging.INFO)
        file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        root.addHandler(file_handler)
        logging.captureWarnings(True)

        for name in (
            "LiteLLM",
            "litellm",
            "httpx",
            "httpcore",
            "urllib3",
            "grpc",
            "google",
            "google.auth",
            "google.api_core",
            "textual",
        ):
            lg = logging.getLogger(name)
            lg.handlers.clear()
            lg.propagate = True
            lg.setLevel(logging.CRITICAL)

        os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
        os.environ.setdefault("GLOG_minloglevel", "3")

    def action_interrupt_or_quit(self) -> None:
        """Ctrl+C:
        - If a submission is running: cancel it.
        - Else if the input has text: clear it.
        - Else (input empty): show the quit hint; a second press within the
          window quits.
        """
        if self._submission_worker is not None:
            self._submission_worker.cancel()
            self._last_idle_interrupt_ts = 0.0
            return

        inp = self.query_one("#input-bar", Input)
        if inp.value:
            inp.value = ""
            self._last_idle_interrupt_ts = 0.0
            # Land focus in the now-empty input so the user can compose
            # immediately. Matters when Ctrl+C is pressed while a result
            # widget is focused.
            inp.focus()
            return

        self._confirm_idle_quit("Ctrl+C", inp)

    def action_quit_only(self) -> None:
        """Ctrl+D:
        - Never interrupts a running submission.
        - Else mirrors idle quit behavior (double press within the window).
        """
        if self._submission_worker is not None:
            return

        inp = self.query_one("#input-bar", Input)
        if inp.value:
            inp.value = ""
            self._last_idle_interrupt_ts = 0.0
            inp.focus()
            return

        self._confirm_idle_quit("Ctrl+D", inp)

    def _confirm_idle_quit(self, key: str, inp: Input) -> None:
        """Quit only when the same idle quit key is pressed twice."""
        import time

        now = time.monotonic()
        if (
            self._last_quit_hint_key == key
            and (now - self._last_idle_interrupt_ts) < self._INTERRUPT_DOUBLE_PRESS_WINDOW
        ):
            self._request_exit()
            return

        self._last_idle_interrupt_ts = now
        self._last_quit_hint_key = key
        if self._saved_input_placeholder is None:
            self._saved_input_placeholder = inp.placeholder
        inp.placeholder = f"Press {self._last_quit_hint_key} again to quit"
        self.set_timer(self._INTERRUPT_DOUBLE_PRESS_WINDOW, self._restore_input_placeholder)

    def _request_exit(self) -> None:
        """Single quit path: disconnect all registered connectors, then
        exit the app.  Every quit trigger (slash command, idle Ctrl+C /
        Ctrl+D double-press, …) routes through here so DB connections
        and DuckDB file locks are always released cleanly.
        """
        if self._session is None:
            self._cleanup_runtime_paths()
            self.exit()
            return
        self.run_worker(self._shutdown_then_exit(), exclusive=False, group="shutdown")

    def _cleanup_runtime_paths(self) -> None:
        """Stop session-local services and remove transient runtime files."""
        import shutil

        if self._pane is not None:
            self._pane.stop()
            self._pane = None
        shutil.rmtree(self._runtime_paths.scratch_dir, ignore_errors=True)

    async def _shutdown_then_exit(self) -> None:
        assert self._session is not None
        try:
            await self._session.close()
        except Exception:
            logger.debug("session close failed during exit", exc_info=True)
        finally:
            self._cleanup_runtime_paths()
            self.exit()

    def _ensure_pane(self) -> "OutputPane | None":
        """Start the output pane if needed; return it, or None if it couldn't start."""
        if self._pane is None:
            from tabulaflow.app.pane import OutputPane

            try:
                ensure_pane_dir(self._runtime_paths.pane_dir)
                self._pane = OutputPane(
                    self._runtime_paths.pane_dir,
                    host=self._output_pane_host,
                    port=self._output_pane_port,
                    public_url=self._output_pane_public_url,
                )
                self._pane.start()
                self._refresh_bottom_status()
            except Exception:
                logger.debug("output pane failed to start", exc_info=True)
                self._pane = None
                self._refresh_bottom_status()
        return self._pane

    def view_card_in_pane(self, card: PaneCard, *, title: str | None = None) -> bool:
        """Push an already-written card-data payload to the pane."""
        pane = self._ensure_pane()
        if pane is None or pane.url is None:
            return False
        pane.push(manual_card_turn(card, title=title))
        return True

    def _refresh_bottom_status(self) -> None:
        """Show model status and the persistent pane URL below the input row."""
        try:
            model_status = self.query_one("#bottom-status-model", Static)
            url_status = self.query_one("#bottom-status-url", Static)
        except Exception:
            return
        url = self._pane.url if self._pane is not None else None
        if self._session is not None and self._session.llm_preset is not None:
            profile = self._session.llm_preset.main
            model_label = model_display_name(profile.model, profile.reasoning_effort)
        elif self._session is None and self._llm_selection.preset is not None:
            model_label = model_display_name(
                self._llm_selection.preset.main.model,
                self._llm_selection.preset.main.reasoning_effort,
            )
        else:
            model_label = "LLM off"
        model_status.update(Text(f"{model_label} · {_compact_project_dir(self._project_dir)}", style="dim"))
        url_status.update(Text(f"View output in browser: {url}" if url else "", style="dim"))

    def _start_llm_activation(self, selection: ResolvedLLMSelection) -> None:
        """Initialize the confirmed LLM option in the background."""
        self._llm_activation_in_progress = selection.preset is not None
        self._llm_activation_error = None
        self.run_worker(
            self._activate_llm_option(selection),
            exclusive=True,
            group="llm-activation",
        )

    async def _activate_llm_option(self, selection: ResolvedLLMSelection) -> None:
        """Activate a confirmed preset or LLM off."""
        import asyncio

        preset = selection.preset
        if self._session is None:
            await self._show_initialization_spinner("Initializing session...")
        try:
            session = await self._ensure_session()
        except Exception as error:
            logger.debug("Session initialization failed", exc_info=True)
            await self._report_session_initialization_failure(error)
            return
        if preset is None:
            if selection.selection is None:
                status = "✓ LLM off · no supported API key detected. Choose a preset in /config."
            else:
                status = "✓ LLM off · /connect and the data explorer remain available."
            await self._publish_initialization_status(
                Text(status, style="dim"),
            )
            return
        await self._show_initialization_spinner("Initializing agent...")
        try:
            keys = await asyncio.to_thread(self._initialize_llm_runtime, session, preset)
        except Exception as error:
            logger.debug("LLM preset initialization failed", exc_info=True)
            await self._finish_llm_activation(selection, result=error)
            return
        await self._finish_llm_activation(selection, result=keys)

    @staticmethod
    def _initialize_llm_runtime(
        session: AppState,
        preset: LLMPreset,
    ) -> tuple[str | None, str | None]:
        return session.activate_llm_preset(preset)

    async def _show_initialization_spinner(self, label: str) -> None:
        if self._initialization_spinner is not None:
            self._initialization_spinner.update_label(label)
            return
        spinner = SpinnerWidget(label)
        self._initialization_spinner = spinner
        chat_log = self.query_one("#chat-log", VerticalScroll)
        await chat_log.mount(spinner)
        chat_log.scroll_end(animate=False)

    async def _remove_initialization_spinner(self) -> None:
        spinner = self._initialization_spinner
        self._initialization_spinner = None
        if spinner is not None:
            await spinner.remove()

    async def _publish_initialization_status(self, message: Text) -> None:
        """Replace the initialization spinner with ``message``."""
        await self._remove_initialization_spinner()
        chat_log = self.query_one("#chat-log", VerticalScroll)
        await chat_log.mount(SystemMessage(message))
        chat_log.scroll_end(animate=False)

    async def _report_session_initialization_failure(self, error: Exception) -> None:
        message = Text.from_markup(f"[{ERROR}]Session initialization failed:[/] ")
        detail = _sanitize_exception_message(error)
        message.append(f"{type(error).__name__}: {detail}" if detail else f"{type(error).__name__}.")
        await self._publish_initialization_status(message)
        self._llm_activation_in_progress = False

    async def _finish_llm_activation(
        self,
        selection: ResolvedLLMSelection,
        *,
        result: tuple[str | None, str | None] | Exception,
    ) -> None:
        preset = selection.preset
        if preset is None:
            raise RuntimeError("Cannot finish activation without an LLM preset.")
        if isinstance(result, Exception):
            self._llm_activation_error = _normalize_llm_activation_error(result, preset)
            message = Text.from_markup(f"[{ERROR}]LLM unavailable:[/] ")
            message.append(self._llm_unavailable_message())
        else:
            self._llm_activation_error = None
            message = _llm_preset_success_message(
                preset,
                result,
                detected_api_key_env=selection.detected_api_key_env,
            )
        await self._publish_initialization_status(message)
        self._llm_activation_in_progress = False
        input_bar = self.query_one("#input-bar", Input)
        if len(self.screen_stack) == 1:
            input_bar.focus()

    def _llm_unavailable_message(self) -> str:
        if self._llm_activation_error is None:
            return LLM_UNAVAILABLE_MESSAGE
        return f"{self._llm_activation_error} /connect and browsing remain available."

    async def _push_turn_to_pane(
        self,
        result: "ChatResult",
        resolved_output: "ResolvedOutput",
        turn_output: TurnOutput,
        *,
        title: str,
        user_text: str,
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
            return
        if not resolved_output.artifacts and not user_text and not result.text:
            return
        pane = self._ensure_pane()
        if pane is None:
            return

        panel = _pane_panel(result)

        async def render_and_push() -> None:
            cards = await render_resolved_output(resolved_output, pane_dir)
            if cards or user_text or result.text:
                pane.push(
                    turn_payload(title=title, user=user_text, assistant=result.text, cards=cards, panel=panel),
                    turn_output=turn_output if panel is not None else None,
                )

        def log_background_error(task: asyncio.Task[None]) -> None:
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                return
            if exc is not None:
                logger.debug("output pane push failed", exc_info=(type(exc), exc, exc.__traceback__))

        task = asyncio.create_task(render_and_push())
        task.add_done_callback(log_background_error)

    def _restore_input_text(self, text: str) -> None:
        """Put `text` back into the input bar and focus it. Used after a
        cancelled turn so the user can edit and resubmit. If the input
        already has content (the user started typing something new during
        the turn), leave it alone."""
        try:
            inp = self.query_one("#input-bar", Input)
        except Exception:
            return
        if inp.value:
            return
        inp.value = text
        inp.cursor_position = len(text)
        inp.focus()

    def _restore_input_placeholder(self) -> None:
        import time

        if (time.monotonic() - self._last_idle_interrupt_ts) < self._INTERRUPT_DOUBLE_PRESS_WINDOW:
            return
        if self._saved_input_placeholder is None:
            return
        try:
            inp = self.query_one("#input-bar", Input)
        except Exception:
            return
        inp.placeholder = self._saved_input_placeholder
        self._saved_input_placeholder = None

    def action_toggle_focus(self) -> None:
        """Toggle focus between input bar and result widgets."""
        inp = self.query_one("#input-bar", Input)
        if inp.has_focus:
            # Jump to the last result widget
            results = self.query(AgentResultWidget)
            if results:
                results.last().focus()
                results.last().scroll_visible()
        else:
            inp.focus()

    async def _ensure_session(self) -> AppState:
        """Get or create the session, initializing in a thread to avoid blocking the UI."""
        if self._session is not None:
            return self._session
        import asyncio

        from tabulaflow.app.state import create_workspace_connector

        async with self._session_lock:
            if self._session is not None:
                return self._session
            loop = asyncio.get_running_loop()
            # The workspace connector must be built on this (main) event loop, but its
            # first import pulls in the heavy sqlalchemy/duckdb/agent stack (~3s cold) —
            # which would freeze the UI. Warm that import off the UI thread first, so
            # both the workspace creation and the construction below stay responsive.
            await loop.run_in_executor(None, _warm_session_imports)
            self._runtime_paths.scratch_dir.mkdir(parents=True, exist_ok=True)
            workspace = await create_workspace_connector(self._runtime_paths.workspace_db_path)
            from functools import partial

            session = await loop.run_in_executor(
                None,
                partial(
                    AppState,
                    llm_preset=self._llm_selection.preset,
                    trajectories_dir=self._runtime_paths.trajectories_dir,
                    data_dir=self._runtime_paths.data_dir,
                    workspace=workspace,
                    project_dir=self._project_dir,
                    scratch_dir=self._runtime_paths.scratch_dir,
                ),
            )
            await self._maybe_autoconnect_sample(session)
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

    async def _maybe_autoconnect_sample(self, session: AppState) -> None:
        """Silently load the bundled sample DB when the user connected nothing of their own."""
        from tabulaflow.app.sample_data import autoconnect_sample

        try:
            await autoconnect_sample(session)
        except Exception:
            pass  # the sample is a convenience; never block startup on it

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        display_text = event.value.strip()
        if not display_text:
            return

        inp = event.input
        if self._submission_worker is not None or self._llm_activation_in_progress:
            inp.focus()
            return

        text = inp.expand_paste_tokens(display_text) if isinstance(inp, HistoryInput) else display_text

        if isinstance(inp, HistoryInput):
            inp.record_submission(display_text)
        event.input.clear()

        self._submission_worker = self.run_worker(
            self._run_submission(text, display_text),
            exclusive=True,
            group="submission",
        )

    async def _run_submission(self, text: str, display_text: str) -> None:
        """Process one accepted input as the active submission."""
        import asyncio

        chat_log = self.query_one("#chat-log", VerticalScroll)
        user_msg = UserMessage(text)
        is_command = text.startswith(COMMAND_PREFIX)
        try:
            await chat_log.mount(user_msg)
            chat_log.scroll_end(animate=False)

            if is_command:
                await self._handle_slash_command(text, chat_log)
                return

            session = await self._ensure_session()
            if not session.registry.list_aliases():
                msg = SystemMessage(Text.from_markup(f"[{ERROR}]No database connected.[/] Use /connect first."))
                await chat_log.mount(msg)
                chat_log.scroll_end(animate=False)
                return

            chat_session = session.active_chat_session
            if chat_session is None:
                error_text = Text.from_markup(f"[{ERROR}]LLM unavailable:[/] ")
                error_text.append(self._llm_unavailable_message())
                await chat_log.mount(SystemMessage(error_text))
                chat_log.scroll_end(animate=False)
                self._refresh_bottom_status()
                return

            await self._run_agent(text, chat_session, chat_log, display_text)
        except asyncio.CancelledError:
            if is_command and user_msg.is_mounted:
                await user_msg.remove()
            await chat_log.mount(SystemMessage("[dim]Interrupted[/dim]"))
            chat_log.scroll_end(animate=False)
            self._restore_input_text(display_text)
            raise
        finally:
            self._submission_worker = None

    @staticmethod
    async def _connect_spinner_label(parts: list[str]) -> str:
        """Build a spinner label for /connect."""
        return "Connecting..."

    async def _handle_slash_command(
        self,
        text: str,
        chat_log: VerticalScroll,
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
            chat_log.scroll_end(animate=False)
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
        result: object,
        session: AppState,
        chat_log: VerticalScroll,
    ) -> None:
        from tabulaflow.app.commands import CommandResult

        assert isinstance(result, CommandResult)

        if result.should_quit:
            self._request_exit()
            return

        if result.should_clear:
            await chat_log.remove_children()
            await chat_log.mount(self._banner_for_preset(session.llm_preset))
            self._refresh_esc_hint()
            return

        if result.should_open_config:
            from tabulaflow.app.screens import ConfigScreen

            self.push_screen(
                ConfigScreen(self._llm_selection),
                self._on_config_closed,
            )
            return

        if result.output is not None:
            msg = SystemMessage(result.output)
            await chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

    def _on_config_closed(self, selection: ResolvedLLMSelection | None) -> None:
        self.call_after_refresh(self.query_one("#input-bar", Input).focus)
        if selection is None:
            return

        session = self._session
        if session is None:
            raise RuntimeError("Config closed before the session was initialized.")
        preset = selection.preset
        session.llm_preset = preset
        self._llm_selection = selection
        update_app_config(llm_preset=selection.selection)
        self._refresh_bottom_status()
        self._start_llm_activation(selection)

    async def _run_agent(
        self,
        question: str,
        chat_session: ChatSession,
        chat_log: VerticalScroll,
        display_text: str,
    ) -> None:
        import asyncio

        from tabulaflow.agents.chat import Finished

        progress = AgentProgressWidget()
        await chat_log.mount(progress)
        chat_log.scroll_end(animate=False)

        result: ChatResult | None = None
        try:
            async for event in chat_session.run_stream(question):
                await progress.apply(event)
                if isinstance(event, Finished):
                    result = event.result
        except asyncio.CancelledError:
            # Freeze the partial progress widget; ChatSession's message history and
            # last_usage already reflect the interrupted run.
            await progress.mark_interrupted(chat_session.last_usage)
            raise
        except Exception as e:
            # Freeze the partial progress widget (mirrors the interrupt path) so the
            # tool steps run so far stay visible, then mount the error below it.
            await progress.mark_failed()
            # Build the detail as plain text (not interpolated into markup) so a
            # ``[...]`` in the exception message can't be parsed as a markup tag.
            error_text = Text.from_markup(f"[{ERROR}]Agent error:[/] ")
            error_text.append(str(e))
            msg = SystemMessage(error_text)
            await chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return
        if result is None:
            return  # normal completion always yields a terminal Finished

        turn_output = TurnOutput(result.output, chat_session.output_store)
        resolved_output = await turn_output.resolve()
        await self._push_turn_to_pane(
            result,
            resolved_output,
            turn_output,
            title=display_text,
            user_text=display_text,
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
            self._refresh_esc_hint()
            # Focus the just-mounted result so the user can press Enter to
            # inspect it without first clicking. The typeahead handler in
            # ``on_key`` routes any printable keystroke back to the input,
            # so this doesn't block fast follow-up prompts. Skip the steal
            # when the user is already composing in the input — yanking
            # focus mid-typing would be hostile.
            inp = self.query_one("#input-bar", Input)
            if not inp.value:
                result_widget.focus()

        # Defer scroll until after layout reflow so the final content height is known.
        self.call_after_refresh(chat_log.scroll_end, animate=False)

    @staticmethod
    def _banner_for_preset(preset: LLMPreset | None) -> BannerWidget:
        return BannerWidget(
            model=preset.main.model if preset is not None else None,
            reasoning_effort=preset.main.reasoning_effort if preset is not None else None,
        )


async def run_tui(
    llm_selection: ResolvedLLMSelection,
    *,
    output_pane_host: str = "127.0.0.1",
    output_pane_port: int | None = None,
    output_pane_public_url: str | None = None,
) -> None:
    """Launch the Textual TUI app."""
    app = TabulaflowApp(
        llm_selection=llm_selection,
        output_pane_host=output_pane_host,
        output_pane_port=output_pane_port,
        output_pane_public_url=output_pane_public_url,
    )
    try:
        await app.run_async(mouse=True)
    finally:
        _restore_terminal_modes()
