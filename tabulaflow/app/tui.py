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
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Static

from tabulaflow.app.commands import COMMAND_PREFIX, handle_command
from tabulaflow.app.session import SessionState
from tabulaflow.app.debug import debug_enabled, mount_debug_widgets
from tabulaflow.app.runtime_paths import RuntimePaths, generate_session_id, prune_old_dumps
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
    from tabulaflow.chat import ChatResult

logger = logging.getLogger(__name__)


def _warm_session_imports() -> None:
    """Import the workspace connector's sqlalchemy/duckdb stack off the UI thread.

    ``create_workspace_connector`` runs on the main event loop (the async engine is
    loop-bound), so its first import of this stack (~0.7s cold) would briefly freeze
    the UI during the background session build. Warming it in the executor first keeps
    the UI responsive. The agent's other heavy imports happen in the executor-thread
    ``SessionState`` construction, so they need no warming here."""
    import tabulaflow.core.db_connector.sql_conn  # noqa: F401


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
        ("ctrl+b", "open_results_pane", "Open results pane"),
        Binding("pageup", "scroll_log('pageup')", "Scroll up", show=False, priority=True),
        Binding("pagedown", "scroll_log('pagedown')", "Scroll down", show=False, priority=True),
    ]

    _INTERRUPT_DOUBLE_PRESS_WINDOW = 1.0

    def __init__(self, *, model: str, agent: str, reasoning_effort: str) -> None:
        import asyncio

        super().__init__()
        self._model = model
        self._agent = agent
        self._reasoning_effort = reasoning_effort
        self._session_id = generate_session_id()
        self._runtime_paths = RuntimePaths.for_session(self._session_id)
        # The directory the app was launched from — the user's project, where source
        # data lives and what relative paths resolve against. Captured once at startup.
        # INVARIANT: the process must never chdir. The shell tool uses this captured
        # value as its cwd, while in-process run_query/DuckDB (COPY, read_csv_auto, …)
        # resolve relative paths against the *live* process cwd; the "relative = project
        # dir" design holds only while those two stay equal, i.e. cwd never changes.
        self._project_dir = Path(os.getcwd())
        prune_old_dumps()
        self._session: SessionState | None = None
        self._pane: OutputPane | None = None
        self._session_lock = asyncio.Lock()
        self._busy = False
        self._current_worker: object | None = None
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
        with Horizontal(id="input-row"):
            # Mint heavy vertical bar — UserMessage-style prompt indicator.
            # Rendered as a single-glyph Static (rather than a CSS border
            # on the input) so the bar height equals one row even though
            # the input bar occupies the full 3-row dock height.
            yield Static("┃", id="input-prompt")
            yield HistoryInput(
                history_path=self._runtime_paths.history_path,
                placeholder="Ask a question or type /help",
                id="input-bar",
            )
            # Dim thin separators between dock sections. Same single-glyph
            # trick: 1-row visual in a 3-row container.
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

    def on_mount(self) -> None:
        self._setup_logging()
        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.mount(BannerWidget(model=self._model, reasoning_effort=self._reasoning_effort))
        if debug_enabled():
            mount_debug_widgets(self, chat_log)
        self.query_one("#input-bar", Input).focus()
        chat_log.scroll_end(animate=False)
        self._refresh_esc_hint()
        self.run_worker(self._ensure_session())

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
        text = self.screen.get_selected_text()
        if text:
            self._copy_to_clipboard(text)

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
            subprocess.run(cmd, input=text.encode("utf-8"), check=False)
        except Exception:
            pass

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
        # for view nav on AgentResultWidget, or ``j``/``k`` for record
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
        - If a turn is running: cancel it.
        - Else if the input has text: clear it.
        - Else (input empty): show the quit hint; a second press within the
          window quits.
        """
        if self._busy and self._current_worker is not None:
            self._current_worker.cancel()  # type: ignore[attr-defined]
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
        - Never interrupts a running turn.
        - Else mirrors idle quit behavior (double press within the window).
        """
        if self._busy:
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
            self.exit()
            return
        self.run_worker(self._shutdown_then_exit(), exclusive=False, group="shutdown")

    async def _shutdown_then_exit(self) -> None:
        assert self._session is not None
        try:
            await self._session.chat_agent.aclose()
        except Exception:
            logger.debug("chat_agent.aclose failed during exit", exc_info=True)
        try:
            await self._session.registry.disconnect_all_async()
        except Exception:
            logger.debug("disconnect_all_async failed during exit", exc_info=True)
        finally:
            # Transient agent working files don't outlive the session.
            import shutil

            if self._pane is not None:
                self._pane.stop()
            shutil.rmtree(self._runtime_paths.scratch_dir, ignore_errors=True)
            self.exit()

    def _ensure_pane(self) -> "OutputPane | None":
        """Lazily start the output pane; return it, or None if it couldn't start."""
        if self._pane is None:
            from tabulaflow.app.pane import OutputPane

            try:
                self._runtime_paths.dumps_dir.mkdir(parents=True, exist_ok=True)
                self._pane = OutputPane(self._runtime_paths.dumps_dir)
                self._pane.start()
            except Exception:
                logger.debug("output pane failed to start", exc_info=True)
                self._pane = None
        return self._pane

    def view_in_pane(self, path: Path) -> bool:
        """Push an already-written dump file to the pane and raise it (manual view).

        Returns True when the pane is available and the artifact was shown, so
        callers can fall back to a direct file open otherwise.
        """
        pane = self._ensure_pane()
        if pane is None or pane.url is None:
            return False
        pane.push(path)
        pane.reopen()
        return True

    def action_open_results_pane(self) -> None:
        """(Re)open the live results pane in the browser (ctrl+b)."""
        pane = self._ensure_pane()
        if pane is not None and pane.url is not None:
            pane.reopen()
        else:
            self.notify("Results pane unavailable.", severity="warning")

    async def _push_results_to_pane(self, result: "ChatResult", chat_log: VerticalScroll) -> None:
        """Render each cited result to the dumps dir and push it to the browser pane.

        Auto-push path: the pane lazily starts and opens once on the first result,
        then updates silently (no focus steal). Best-effort — any failure is
        swallowed so the pane never blocks or fails a chat turn.
        """
        import secrets

        from tabulaflow.app.render import render_chart_html, render_table_html

        started = self._pane is None
        pane = self._ensure_pane()
        if pane is None:
            return
        dumps_dir = self._runtime_paths.dumps_dir
        for record in result.records:
            if record.df is None or record.df.empty:
                continue
            try:
                if record.chart_spec is not None:
                    path = dumps_dir / f"V_{secrets.token_hex(3)}.html"
                    render_chart_html(record.df, record.chart_spec, path, title=record.label)
                else:
                    path = dumps_dir / f"T_{secrets.token_hex(3)}.html"
                    render_table_html(record.df, path, title=record.label)
            except Exception:
                logger.debug("output pane render failed", exc_info=True)
                continue
            pane.push(path)

        if started and pane.url is not None:
            await chat_log.mount(
                SystemMessage(Text(f"Results pane → {pane.url}  ·  ctrl+b to reopen", style="dim"))
            )
            pane.open_browser()

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

    async def _ensure_session(self) -> SessionState:
        """Get or create the session, initializing in a thread to avoid blocking the UI."""
        if self._session is not None:
            return self._session
        import asyncio

        from tabulaflow.app.session import create_workspace_connector

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
            session = await loop.run_in_executor(
                None,
                SessionState,
                self._model,
                self._agent,
                self._session_id,
                self._runtime_paths.trajectories_dir,
                self._runtime_paths.data_dir,
                workspace,
                self._reasoning_effort,
                self._project_dir,
                self._runtime_paths.scratch_dir,
            )
            await self._maybe_autoconnect_sample(session)
            self._enable_explorer_button()
            # Publish the session only once it is fully ready (sample autoconnected,
            # explorer enabled). The early-return guards above key off ``self._session``,
            # so setting it sooner would let an early question proceed mid-setup.
            self._session = session
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

    async def _maybe_autoconnect_sample(self, session: SessionState) -> None:
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

        if self._busy:
            return

        inp = event.input
        text = inp.expand_paste_tokens(display_text) if isinstance(inp, HistoryInput) else display_text

        event.input.clear()

        chat_log = self.query_one("#chat-log", VerticalScroll)

        if text.startswith(COMMAND_PREFIX):
            self._busy = True
            user_msg = UserMessage(text)
            await chat_log.mount(user_msg)
            chat_log.scroll_end(animate=False)
            self._current_worker = self.run_worker(self._handle_slash_command(text, chat_log, user_msg, display_text))
            return

        session = await self._ensure_session()

        if not session.registry.list_aliases():
            await chat_log.mount(UserMessage(text))
            msg = SystemMessage(Text.from_markup(f"[{ERROR}]No database connected.[/] Use /connect first."))
            await chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return

        user_msg = UserMessage(text)
        await chat_log.mount(user_msg)
        chat_log.scroll_end(animate=False)

        self._busy = True
        self._current_worker = self.run_worker(
            self._run_agent(text, session, chat_log, user_msg, display_text), exclusive=True, group="agent"
        )

    @staticmethod
    async def _connect_spinner_label(parts: list[str]) -> str:
        """Build a spinner label for /connect."""
        return "Connecting..."

    async def _handle_slash_command(
        self,
        text: str,
        chat_log: VerticalScroll,
        user_msg: UserMessage,
        display_text: str | None = None,
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

        import asyncio

        try:
            session = await self._ensure_session()
            result = await handle_command(text, session)
        except asyncio.CancelledError:
            await user_msg.remove()
            await chat_log.mount(SystemMessage("\n[dim]Interrupted[/dim]"))
            chat_log.scroll_end(animate=False)
            self._restore_input_text(display_text if display_text is not None else text)
            raise
        finally:
            self._busy = False
            self._current_worker = None
            if spinner is not None:
                await spinner.remove()

        self._show_command_result(result, session, chat_log)

    def _show_command_result(
        self,
        result: object,
        session: SessionState,
        chat_log: VerticalScroll,
    ) -> None:
        from tabulaflow.app.commands import CommandResult

        assert isinstance(result, CommandResult)

        if result.should_quit:
            self._request_exit()
            return

        if result.password_prompt:
            msg = SystemMessage(
                "[dim]Password-protected connections: include the password in the URL "
                "or set it via environment variables.[/dim]"
            )
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return

        if result.should_clear:
            chat_log.remove_children()
            chat_log.mount(BannerWidget(model=session.model, reasoning_effort=session.reasoning_effort))
            return

        if result.output is not None:
            msg = SystemMessage(result.output)
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

    async def _run_agent(
        self,
        question: str,
        session: SessionState,
        chat_log: VerticalScroll,
        user_msg: UserMessage,
        display_text: str | None = None,
    ) -> None:
        import asyncio

        from tabulaflow.chat import Finished

        progress = AgentProgressWidget()
        await chat_log.mount(progress)
        chat_log.scroll_end(animate=False)

        result: ChatResult | None = None
        try:
            async for event in session.chat_agent.run_stream(question):
                progress.apply(event)
                if isinstance(event, Finished):
                    result = event.result
        except asyncio.CancelledError:
            # Freeze the partial progress widget; ChatAgent's message history and
            # last_usage already reflect the interrupted run.
            progress.mark_interrupted(session.chat_agent.last_usage)
            await chat_log.mount(SystemMessage("[dim]Interrupted[/dim]"))
            chat_log.scroll_end(animate=False)
            self._restore_input_text(display_text if display_text is not None else question)
            raise
        except Exception as e:
            # Freeze the partial progress widget (mirrors the interrupt path) so the
            # tool steps run so far stay visible, then mount the error below it.
            progress.mark_failed()
            # Build the detail as plain text (not interpolated into markup) so a
            # ``[...]`` in the exception message can't be parsed as a markup tag.
            error_text = Text.from_markup(f"[{ERROR}]Agent error:[/] ")
            error_text.append(str(e))
            msg = SystemMessage(error_text)
            await chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return
        finally:
            self._busy = False
            self._current_worker = None

        if result is None:
            return  # normal completion always yields a terminal Finished

        session.last_result = result
        if result.records:
            # Push to the browser pane BEFORE building the widget: AgentResultWidget
            # -> build_result_views() nulls each record.df after rendering to Rich.
            await self._push_results_to_pane(result, chat_log)
            # chat-log padding (2) + scrollbar (2) + widget margin (5) + widget padding (2) = 11
            result_widget = AgentResultWidget(
                result,
                width=self.size.width - 11,
                query_history=session.chat_agent.query_history,
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


async def run_tui(model: str, agent: str, reasoning_effort: str) -> None:
    """Launch the Textual TUI app."""
    app = TabulaflowApp(model=model, agent=agent, reasoning_effort=reasoning_effort)
    await app.run_async()
