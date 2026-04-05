"""Textual TUI application for mintq interactive chat."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input

from mintq.cli.commands import COMMAND_PREFIX, SessionState, handle_command
from mintq.cli.widgets import (
    AgentProgressWidget,
    AgentResultWidget,
    BannerWidget,
    HistoryInput,
    SpinnerWidget,
    SystemMessage,
    UserMessage,
)

if TYPE_CHECKING:
    from mintq.cli.agent import ChatResult

DATA_DIR = Path.home() / ".mintq"

logger = logging.getLogger(__name__)


class MintqApp(App[None]):
    """Interactive database chat TUI."""

    CSS_PATH = "tui.tcss"

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("escape", "toggle_focus", "Toggle focus"),
    ]

    def __init__(self, *, model: str, agent: str) -> None:
        import asyncio

        super().__init__()
        self._model = model
        self._agent = agent
        self._session: SessionState | None = None
        self._session_lock = asyncio.Lock()
        self._agent_busy = False

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat-log")
        yield HistoryInput(
            history_path=DATA_DIR / "history",
            placeholder="Ask a question or type /help",
            id="input-bar",
        )

    def on_mount(self) -> None:
        self._setup_logging()
        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.mount(BannerWidget(model=self._model))
        self.query_one("#input-bar", Input).focus()
        self.run_worker(self._ensure_session())

    def _setup_logging(self) -> None:
        from logging.handlers import RotatingFileHandler

        log_dir = DATA_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "cli.log"

        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.DEBUG)
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

        async with self._session_lock:
            if self._session is not None:
                return self._session
            loop = asyncio.get_running_loop()
            self._session = await loop.run_in_executor(
                None, SessionState, self._model, self._agent
            )
            return self._session

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        if self._agent_busy:
            return

        event.input.clear()

        chat_log = self.query_one("#chat-log", VerticalScroll)

        if text.startswith(COMMAND_PREFIX):
            chat_log.mount(UserMessage(text))
            chat_log.scroll_end(animate=False)
            self.run_worker(self._handle_slash_command(text, chat_log))
            return

        session = await self._ensure_session()

        if not session.registry.list_aliases():
            chat_log.mount(UserMessage(text))
            msg = SystemMessage("[red]No database connected.[/red] Use /connect first.")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return

        chat_log.mount(UserMessage(text))
        chat_log.scroll_end(animate=False)

        self._agent_busy = True
        self.run_worker(self._run_agent(text, session, chat_log), exclusive=True)

    async def _handle_slash_command(
        self,
        text: str,
        chat_log: VerticalScroll,
    ) -> None:
        parts = text.split()
        cmd = parts[0].lower() if parts else ""
        slow = cmd in {"/connect", "/disconnect"}

        spinner: SpinnerWidget | None = None
        if slow:
            label = "Connecting..." if cmd == "/connect" else "Disconnecting..."
            spinner = SpinnerWidget(label)
            chat_log.mount(spinner)
            chat_log.scroll_end(animate=False)

        try:
            session = await self._ensure_session()
            result = await handle_command(text, session)
        finally:
            if spinner is not None:
                await spinner.remove()

        self._show_command_result(result, session, chat_log)

    def _show_command_result(
        self,
        result: object,
        session: SessionState,
        chat_log: VerticalScroll,
    ) -> None:
        from mintq.cli.commands import CommandResult

        assert isinstance(result, CommandResult)

        if result.should_quit:
            self.exit()
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
            chat_log.mount(BannerWidget(model=session.model))
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
    ) -> None:
        progress = AgentProgressWidget()
        chat_log.mount(progress)
        chat_log.scroll_end(animate=False)

        try:
            result: ChatResult = await session.chat_agent.run(question, progress)
        except Exception as e:
            await progress.remove()
            msg = SystemMessage(f"[red]Agent error:[/red] {e}")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return
        finally:
            self._agent_busy = False

        if progress._streaming_text != result.text:
            progress._streaming_text = result.text
            progress._refresh(layout=True)

        session.last_result = result
        result_widget = AgentResultWidget(result, width=self.size.width - 4)
        chat_log.mount(result_widget)
        chat_log.scroll_end(animate=False)


async def run_tui(model: str, agent: str) -> None:
    """Launch the Textual TUI app."""
    app = MintqApp(model=model, agent=agent)
    await app.run_async()
