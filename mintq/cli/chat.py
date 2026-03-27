"""Interactive chat session loop."""

from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from mintq.cli.agent import ChatAgent, ChatResult
from mintq.cli.commands import handle_command, COMMAND_PREFIX
from mintq.cli.connections import ConnectionManager
from mintq.cli.display import print_banner, view_result

DATA_DIR = Path.home() / ".mintq"

console = Console()


class ChatSession:
    """Holds state for a single interactive session."""

    def __init__(self, model: str, agent: str) -> None:
        self.model = model
        self.agent_name = agent
        self.connections = ConnectionManager()
        self.output_modes: set[str] = {"nl"}
        self.chat_agent = ChatAgent(model=model)
        self.last_result: ChatResult | None = None

    @property
    def prompt_text(self) -> str:
        active = self.connections.active_alias
        if active:
            return f"[{active}] ❯ "
        return "❯ "


async def run_chat(model: str, agent: str) -> None:
    """Main chat loop driven by prompt_toolkit."""
    import logging

    import mintq

    mintq.configure()
    logging.getLogger("mintq").setLevel(logging.CRITICAL)

    session = ChatSession(model=model, agent=agent)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prompt_session: PromptSession[str] = PromptSession(
        history=FileHistory(str(DATA_DIR / "history")),
    )

    print_banner(console, model=model, agent=agent)

    while True:
        try:
            user_input = await prompt_session.prompt_async(session.prompt_text)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

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
