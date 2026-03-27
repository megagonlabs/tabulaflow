"""Interactive chat session loop."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

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

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("mintq").setLevel(logging.CRITICAL)

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

    while True:
        console.print()
        prompt = session.prompt_parts if session else default_prompt
        try:
            user_input = await prompt_session.prompt_async(
                prompt, prompt_continuation=_continuation,
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
            should_quit = await handle_command(text, session, console)
            if should_quit:
                break
            continue

        connector = session.connections.active_connector
        if connector is None:
            console.print("[red]No database connected.[/red] Use /connect first.")
            continue

        try:
            result = await session.chat_agent.run(text, connector, console)
        except Exception as e:
            console.print(f"[red]Agent error:[/red] {e}")
            continue

        session.last_result = result
        console.print()
        await view_result(console, result)
