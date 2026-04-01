"""Interactive chat session loop."""

from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.history import FileHistory
from rich.console import Console

from mintq.cli.commands import handle_command, COMMAND_PREFIX
from mintq.cli.display import print_banner, view_result
from mintq.cli.theme import ACCENT_BOLD

if TYPE_CHECKING:
    from mintq.cli.agent import ChatAgent, ChatResult
    from mintq.cli.connections import ConnectionManager

DATA_DIR = Path.home() / ".mintq"

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

    def __init__(self, model: str, agent: str) -> None:
        from mintq.cli.agent import ChatAgent
        from mintq.cli.connections import ConnectionManager

        self.model = model
        self.agent_name = agent
        self.connections: ConnectionManager = ConnectionManager()
        self.output_modes: set[str] = {"nl"}
        self.chat_agent: ChatAgent = ChatAgent(model=model)
        self.last_result: ChatResult | None = None

    @property
    def prompt_parts(self) -> list[tuple[str, str]]:
        return [("class:prompt-bar", "┃"), ("", " ")]


def _init_session_sync(model: str, agent: str) -> ChatSession:
    """Initialize ChatSession (runs heavy imports)."""
    return ChatSession(model=model, agent=agent)


async def run_chat(model: str, agent: str) -> None:
    """Main chat loop driven by prompt_toolkit."""
    import logging
    import os
    import sys
    from logging.handlers import RotatingFileHandler

    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "cli.log"

    # Route all Python logging to file only. Keep terminal output reserved for
    # explicit user-facing messages rendered by Rich.
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)
    file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root.addHandler(file_handler)
    logging.captureWarnings(True)

    # Silence noisy third-party loggers in interactive mode.
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

    # Some native libraries (e.g., grpc/absl) write directly to stderr and
    # bypass Python logging. Redirect stderr to the same log file to keep the
    # interactive UI clean.
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
    init_task = loop.run_in_executor(None, _init_session_sync, model, agent)
    session: ChatSession | None = None

    def _continuation(width: int, _line_number: int, _is_soft_wrap: bool) -> AnyFormattedText:
        pad = " " * (width - 2)
        return [("", pad), ("class:prompt-bar", "┃"), ("", " ")]

    default_prompt: AnyFormattedText = [("class:prompt-bar", "┃"), ("", " ")]

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
                with _suppress_native_stderr():
                    should_quit = await handle_command(text, session, console)
                if should_quit:
                    break
                continue

            connector = session.connections.active_connector
            if connector is None:
                console.print("[red]No database connected.[/red] Use /connect first.")
                continue

            try:
                with _suppress_native_stderr():
                    result = await session.chat_agent.run(text, connector, console)
            except Exception as e:
                console.print(f"[red]Agent error:[/red] {e}")
                continue

            session.last_result = result
            console.print()
            await view_result(console, result)
    finally:
        if session is not None:
            await session.connections.disconnect_all()
        sys.stderr = original_stderr
        stderr_stream.close()
