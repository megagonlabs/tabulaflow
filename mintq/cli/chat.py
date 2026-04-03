"""Interactive chat session loop."""

from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
from typing import TYPE_CHECKING, Awaitable, Callable, Iterator

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.history import FileHistory
from rich.console import Console

from mintq.cli.display import print_banner, view_result
from mintq.cli.theme import ACCENT_BOLD

if TYPE_CHECKING:
    from mintq.cli.agent import ChatAgent, ChatResult
    from mintq.db_connector.db_registry import DBRegistry

DATA_DIR = Path.home() / ".mintq"
COMMAND_PREFIX = "/"

console = Console()


@contextmanager
def _suppress_native_stderr() -> Iterator[None]:
    """Silence native writes to stderr (fd=2) during interactive actions."""
    import os

    saved_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, 2)
        yield
    finally:
        os.dup2(saved_fd, 2)
        os.close(saved_fd)
        os.close(devnull_fd)


class ChatSession:
    """Holds state for a single interactive session."""

    def __init__(self, model: str, agent: str, console_width: int) -> None:
        from mintq.cli.agent import ChatAgent
        from mintq.db_connector.db_registry import DBRegistry

        self.agent_name = agent
        self.registry: DBRegistry = DBRegistry()
        self.chat_agent: ChatAgent = ChatAgent(registry=self.registry, console_width=console_width, model=model)
        self.last_result: ChatResult | None = None

    @property
    def model(self) -> str:
        """Return the active model used by the runtime chat agent."""
        return self.chat_agent.model

    def set_model(self, model: str) -> None:
        """Update the runtime chat agent model."""
        self.chat_agent.set_model(model)

    @property
    def prompt_parts(self) -> list[tuple[str, str]]:
        return [("class:prompt-bar", "┃"), ("", " ")]


def _init_session_sync(model: str, agent: str, console_width: int) -> ChatSession:
    """Initialize ChatSession (runs heavy imports)."""
    return ChatSession(model=model, agent=agent, console_width=console_width)


async def run_chat(model: str, agent: str) -> None:
    """Main chat loop driven by prompt_toolkit."""
    import logging
    import os
    import sys
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
    ):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.CRITICAL)

    os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
    os.environ.setdefault("GLOG_minloglevel", "3")
    stderr_stream = open(log_path, "a", encoding="utf-8", buffering=1)
    original_stderr = sys.stderr
    sys.stderr = stderr_stream

    from prompt_toolkit.styles import Style

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prompt_session: PromptSession[str] = PromptSession(
        history=FileHistory(str(DATA_DIR / "history")),
        style=Style.from_dict({"prompt-bar": ACCENT_BOLD}),
    )

    import asyncio

    print_banner(console, model=model, agent=agent)

    loop = asyncio.get_running_loop()
    init_task = loop.run_in_executor(None, _init_session_sync, model, agent, console.width)
    session: ChatSession | None = None

    def _continuation(width: int, _line_number: int, _is_soft_wrap: bool) -> AnyFormattedText:
        pad = " " * (width - 2)
        return [("", pad), ("class:prompt-bar", "┃"), ("", " ")]

    default_prompt: AnyFormattedText = [("class:prompt-bar", "┃"), ("", " ")]
    command_handler: Callable[[str, "ChatSession", Console], Awaitable[bool]] | None = None

    try:
        while True:
            console.print()
            prompt = session.prompt_parts if session else default_prompt
            try:
                user_input = await prompt_session.prompt_async(
                    prompt,  # type: ignore[arg-type]
                    prompt_continuation=_continuation,  # type: ignore[arg-type]
                )
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            if session is None:
                session = await init_task

            text = user_input.strip()
            if not text:
                continue

            if text.startswith(COMMAND_PREFIX):
                if command_handler is None:
                    from mintq.cli.commands import handle_command as imported_handle_command

                    command_handler = imported_handle_command
                with _suppress_native_stderr():
                    should_quit = await command_handler(text, session, console)
                if should_quit:
                    break
                continue

            if not session.registry.list_aliases():
                console.print("[red]No database connected.[/red] Use /connect first.")
                continue

            try:
                with _suppress_native_stderr():
                    result = await session.chat_agent.run(text, console)
            except Exception as e:
                console.print(f"[red]Agent error:[/red] {e}")
                continue

            session.last_result = result
            console.print()
            await view_result(console, result)
    finally:
        if session is not None:
            await session.registry.disconnect_all_async()
        sys.stderr = original_stderr
        stderr_stream.close()
